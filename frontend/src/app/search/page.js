import styles from "../page.module.css";
import SearchComp from "../components/SearchComp";

function SearchPage() {
  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <div className={styles.header}>
          <h2>Data Whisperer</h2>
        </div>
        <div className={styles.content1}>
          <SearchComp/>
        </div>
      </main>
      <footer className={styles.footer}>
        <p>Build by AI Alchemist 111, Powered by Llama Index</p>
      </footer>
    </div>
  )
}

export default SearchPage