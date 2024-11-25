
import Image from "next/image";
import styles from "./page.module.css";
import Link from "next/link";
import FileUpload from "./components/FileUpload";
// import React, { useRef } from "react";

export const revalidate = 10;

export default async function Home() {

  const url = "http://127.0.0.1:5000/files"
  const data = await fetch(url);
  const files = await data.json();

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <div className={styles.header}>
          <h2>Data Whisperer</h2>
        </div>
        <div className={styles.content}>
          <p>To get started, use existing datasets or upload your own.</p>
          <div className={styles.card_container}>
            <FileUpload/>
          </div>
          <hr className={styles.hr}/>
          <p>Available Datasets</p>
          <div className={styles.card_container}>
            {
              files.map((file, index) => (
              <div key={index} className={styles.card_alt}>
                <Link href={`/search?file=${file.filename}`}>
                <Image src={'/csv.svg'} width={30}height={30} style={{filter: 'invert(1)'}} alt="upload icon"/>
                  <h3>{file.filename}</h3>
                  <p>{new Date(file.upload_time).toDateString()}</p>
                </Link>
              </div>
              ))
            }
          </div>
        </div>
      </main>
      <footer className={styles.footer}>
        <p>Build by AI Alchemist 111, Powered by Llama Index</p>
      </footer>
    </div>
  );
}
