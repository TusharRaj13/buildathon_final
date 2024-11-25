'use client'
import React, { useRef, useState } from 'react';
import styles from "../page.module.css";
import Image from 'next/image';


function FileUpload() {

  const fileInputRef = useRef(null);
  const [loading, setloading] = useState(false)

  // Function to trigger file input click
  const handleDivClick = () => {
    fileInputRef.current.click();
  };

  // Function to handle file selection and upload
  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (file) {
      console.log("Selected file:", file);
      setloading(true);
      // Example: Upload the file
      const formData = new FormData();
      formData.append("file", file);

      try {
        const response = await fetch("http://127.0.0.1:5000/upload", {
          method: "POST",
          body: formData,
        });
        const result = await response.json();
        console.log("Upload success:", result);
        if(response.status >= 400) 
          alert(result["error"])
        else
          alert(result["message"])
        setloading(false);
      } catch (error) {
        console.error("Upload failed:", error);
        alert(error("error"))
        setloading(false)
      }
    }
  };


  return (
    <div className={styles.card_alt} onClick={handleDivClick}>
      <Image src={'/upload.svg'} width={50} height={50} style={{ filter: 'invert(1)' }} alt="upload icon" />
      <h3>Upload own dataset</h3>
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      {loading && <div className={styles.loader}>
        Loading...
      </div>}
    </div>
  )
}

export default FileUpload