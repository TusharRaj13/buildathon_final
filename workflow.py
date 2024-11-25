from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context
)

from llama_deploy import (
    deploy_workflow,
    WorkflowServiceConfig,
    ControlPlaneConfig,
)

import asyncio
import sys
import os

from llama_index.core.workflow import draw_all_possible_flows
from llama_index.utils.workflow import draw_all_possible_flows
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import (CSVReader)

# from llama_index.llms.ollama import Ollama
from llama_index.llms.openai import OpenAI

import re
import json
import requests
import matplotlib.pyplot as plt
import base64
from fpdf import FPDF
import time

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", size=12)
        self.cell(0, 10, "PDF Example", align="C", ln=True)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", size=10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

class ESQueryEvent(Event):
    query: str

class ESExecEvent(Event):
    query: str
    json_object: any

# class FailedEvent(Event):
#     query: str
#     event_call: str

class ProcUserQueryEvent(Event):
    query: str

class ProcReport(Event):
    query: str
    report_export_data: any

class GraphGenEvent(Event):
    query: str

class ReportSummaryEvent(Event):
    query: str
    summary: str

class ProcReportExport(Event):
    query: str

class ReportGenFlow(Workflow):

    @step(pass_context=True)
    async def read_csv_file_and_get_headers(self, ctx: Context, ev: StartEvent) -> ESQueryEvent:
        
        f = open(f"./static/uploads/{ev.filename}")
        csv_lines = f.read().split("\n")
        csv_header = csv_lines[0]
        header_values = [value.strip() for value in csv_header.split(",")]
        row1 = csv_lines[1]
        sample_row = [value.strip() for value in row1.split(",")]
        ctx.data["headers"] = header_values
        ctx.data["sample_row"] = sample_row
        # print(header_values, sample_row)
        # return StopEvent(result="")
        return ESQueryEvent(query=ev.query)
    
    @step(pass_context=True)
    async def generate_elastic_search_query(self, ctx: Context, ev: ESQueryEvent) -> ESExecEvent | ESQueryEvent:
        headers = ctx.data["headers"]
        sample_row = ctx.data["sample_row"]
        os.environ["OPENAI_API_KEY"] = ""
        # llm = Ollama(model="llama3.1", request_timeout=120.0)
        llm = OpenAI(
            model="gpt-4o-mini",
        )
        prompt = f"Respond only the JSON for elasticsearch aggregation query (apply filter until specified & size = 0 & no field has fielddata enabled) where field names are {headers} and a sample row is as follows {sample_row}. Query - {ev.query} "
        # print(prompt)
        response = await llm.acomplete(prompt)
        match = re.search(r"```json\n(.*?)\n```", str(response), re.DOTALL)
        # json_text = match.group(1)
        # json_object = json.loads(json_text)
        # return ESExecEvent(query=ev.query, json_text=json_object)
        # print(str(response))
        if match:
            json_text = match.group(1)
            try:
                json_object = json.loads(json_text)
                return ESExecEvent(query=ev.query, json_object=json_object)
            except json.JSONDecodeError as e:
                return ESQueryEvent(query=ev.query)
        else:
            return ESQueryEvent(query=ev.query)
        # return StopEvent(result=str(response))

    @step(pass_context=True)
    async def execute_es_query(self, ctx: Context, ev: ESExecEvent) -> ProcUserQueryEvent | ESQueryEvent:
        es_url = "http://localhost:9200"
        index_name = "csv_index"
        response =  requests.post(f"{es_url}/{index_name}/_search", headers={"Content-Type": "application/json"}, data=json.dumps(ev.json_object))
        if response.status_code == 200:
            # Parse the response as JSON
            result = response.json()
            agg_data = result["aggregations"]
            final_result = []
            for key in agg_data:
                obj = {
                    "title": key.replace("_", " ").title(),
                    "data": agg_data[key]["buckets"]
                }
                final_result.append(obj)
            ctx.data["es_result"] = final_result
            return ProcUserQueryEvent(query=ev.query)
        else:
            # print(f"Error: {response.status_code}, {response.text}")
            return ESQueryEvent(query=ev.query)
        
    @step(pass_context=True)
    async def process_user_query(self, ctx: Context, ev: ProcUserQueryEvent) -> ProcReport | ProcUserQueryEvent:
        os.environ["OPENAI_API_KEY"] = ""
        # llm = Ollama(model="llama3.1", request_timeout=120.0)
        llm = OpenAI(
            model="gpt-4o-mini",
        )
        prompt = f"Respond only the JSON for given user query '{ev.query}'; extract graph type (field name: graph_type, values: [bar chart, line graph, pie chart], if not specified then give best fit according to query) & extract output file (field name: output_file, values: [PDF, DOC, HTML], if not speficied then set HTML)"
        response = await llm.acomplete(prompt)
        match = re.search(r"```json\n(.*?)\n```", str(response), re.DOTALL)
        if match:
            json_text = match.group(1)
            try:
                json_object = json.loads(json_text)
                ctx.data["export_config"] = json_object
                return ProcReport(query=ev.query, report_export_data=json_object)
            except json.JSONDecodeError as e:
                return ProcUserQueryEvent(query=ev.query)
        else:
            return ProcUserQueryEvent(query=ev.query)
        
    @step(pass_context=True)
    async def generate_graphs(self, ctx: Context, ev: ProcReport) -> GraphGenEvent:
        export_config = ev.report_export_data
        graph_value = ctx.data["es_result"]
        # print(graph_value)
        title = graph_value[0]["title"]
        data = graph_value[0]["data"]
        labels = [item["key"] for item in data]
        values = [item["doc_count"] for item in data]
        if(export_config["graph_type"].lower() == "pie chart"):
            plt.title(title)
            plt.pie(values, labels=labels)
            plt.legend()
            plt.savefig(f'./data/images/piechart.jpg')
            ctx.data["img_path"] = f'./data/images/piechart.jpg'
            return GraphGenEvent(query=ev.query)
        elif (export_config["graph_type"].lower() == "bar chart"):
            plt.title(title)
            left = [value for value in range(1, len(labels) + 1)]
            plt.bar(left, height=values, tick_label=labels, width=0.8)
            plt.legend()
            plt.savefig(f'./data/images/barchart.jpg')
            ctx.data["img_path"] = f'./data/images/barchart.jpg'
            return GraphGenEvent(query=ev.query)
        else:
            plt.title(title)
            x = [value for value in range(1, len(labels) + 1)]
            y = values
            plt.plot(x, y)
            plt.xlim(1, len(labels))
            plt.ylim(0, max(values))
            plt.xticks(labels)
            plt.savefig(f'./data/images/linechart.jpg')
            ctx.data["img_path"] = f'./data/images/linechart.jpg'
            return GraphGenEvent(query=ev.query)
        
    
    @step(pass_context=True)
    async def generate_summary(self, ctx: Context, ev: GraphGenEvent) -> ReportSummaryEvent:
        graph_value = ctx.data["es_result"]
        os.environ["OPENAI_API_KEY"] = ""
        # llm = Ollama(model="llama3.1", request_timeout=120.0)
        llm = OpenAI(
            model="gpt-4o-mini",
        )
        prompt = f"Give summary of given json based on query, {json.dumps(graph_value[0])} Query = {ev.query}"
        # print(prompt)
        response = await llm.acomplete(prompt)
        return ReportSummaryEvent(query=ev.query, summary=str(response))
    
    @step(pass_context=True)
    async def generate_export_file(self, ctx: Context, ev: ReportSummaryEvent) -> StopEvent:
        img_path = ctx.data["img_path"]
        export_config = ctx.data["export_config"]
        summary = ev.summary
        if(export_config["output_file"].upper() == "HTML"):
            output_html = "./data/output/output.html"
            with open(img_path, "rb") as image_file:
                base64_img = base64.b64encode(image_file.read()).decode("utf-8")
                html_content = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>HTML Example</title>
                </head>
                <body>
                    <h1>Report</h1>
                    <p>{summary}</p>
                    <img src="data:image/jpeg;base64,{base64_img}" alt="Example Image"/>
                </body>
                </html>
                """
                with open(output_html, "w") as file:
                    file.write(html_content)
                return StopEvent(result=f"output.html")
        else: # Output PDF
            output_pdf = "./data/output/output.pdf"
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, summary)
            pdf.ln(10)
            pdf.image(img_path, x=10, y=50, w=100)  # Adjust x, y, and w as needed
            pdf.output(output_pdf)
            return StopEvent(result=f"output.pdf")

    # async def failed_recall(self, ev: FailedEvent) -> ESQueryEvent:
    #     if(ev.event_call == "generate_es_query"):
    #         return ESQueryEvent(query=ev.query)

    

# async def main(query, filename):
#     w = ReportGenFlow(timeout=None, verbose=False)
#     # draw_all_possible_flows(ReportGenFlow, "workflow.html")
#     # start = time.time()
#     result = await w.run(query=query, filename=filename)
#     # print(time.time() - start)
#     print(result)

async def main():
    # Deploy the workflow as a service
    await deploy_workflow(
        ReportGenFlow(timeout=None, verbose=True),
        WorkflowServiceConfig(
            host="127.0.0.1", port=8002, service_name="report_gen_flow"
        ),
        ControlPlaneConfig(),
    )

if __name__ == "__main__":
    # print(sys.argv[1], sys.argv[2])
    asyncio.run(main())
    

