import { debugLog, errorLog } from '@shared/logger'
import db from '../models'

export const readAllArticle = () => {
  try {
    const query = `SELECT * FROM article`
    const readQuery = db.prepare(query)
    const rowList = readQuery.all()
    return rowList
  } catch (err) {
    errorLog(err)
    throw err
  }
}

export const insertArticle = (data: { title: string; content: string }) => {
  try {
    const { title, content } = data
    const insertQuery = db.prepare(
      `INSERT INTO article (title, content) VALUES (?, ?)`
    )
    const transaction = db.transaction(() => {
      const info = insertQuery.run(title, content)
      debugLog(
        `Inserted ${info.changes} rows with last ID ${info.lastInsertRowid} into article`
      )
    })
    transaction()
  } catch (err) {
    errorLog(err)
    throw err
  }
}

export const deleteAllArticles = () => {
  try {
    const deleteQuery = db.prepare(`DELETE FROM article`)
    const info = deleteQuery.run()
    debugLog(`Deleted ${info.changes} rows from article`)
  } catch (err) {
    errorLog(err)
    throw err
  }
}
