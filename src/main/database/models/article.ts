import Database from 'better-sqlite3'
import { debugLog, errorLog } from '@shared/logger'

const initArticleTable = (db: Database.Database) => {
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

export default initArticleTable
