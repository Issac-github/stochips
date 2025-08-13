import { debugLog, errorLog } from '@shared/logger'
import db from '..'

export const initializeDatabase = () => {
  try {
    const createTableQuery = `
      CREATE TABLE IF NOT EXISTS article (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `
    db.exec(createTableQuery)
    debugLog('Article table initialized successfully')
  } catch (err) {
    errorLog('Error initializing database:', err)
    throw err
  }
}

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
