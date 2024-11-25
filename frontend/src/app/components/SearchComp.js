'use client'
import React, { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import styles from "../page.module.css";

function SearchComp() {

  const [loading, setloading] = useState(false);
  const [output_file_path, setoutput_file_path] = useState('')
  const [query, setquery] = useState('')
  const searchparam = useSearchParams();

  const filename = searchparam.get('file');

  const handleBtnClick = async () => {
    setloading(true)
    try {
      const response = await fetch("http://127.0.0.1:5000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          filename: filename
        }),
      });
  
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
  
      const result = await response.json();
      console.log("Success:", result);
      let ff = result["output_file"]
      setoutput_file_path(`http://127.0.0.1:5000/download/${ff}`)
      setloading(false);
      return result;
    } catch (error) {
      setloading(false);
      console.error("Error:", error);
      throw error;
    }
  }

  return (
    <div className={styles.search_comp}>
      <input className={styles.search_input} type='text' onChange={($event) => setquery($event.target.value)}/>
      <button className={styles.search_btn} onClick={() => handleBtnClick()}>Generate Report</button>
      {loading && <div className={styles.loader}>
        Loading...
      </div>}
      { output_file_path && <a className='anchor' href={output_file_path} target='_blank'>Download File</a> }
    </div>
  )
}

export default SearchComp