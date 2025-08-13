/* eslint-disable no-console */
export const debugLog = (...args: unknown[]) => {
  if (!import.meta.env.PROD) {
    console.log(...args)
  }
}

export const errorLog = (...args: unknown[]) => {
  console.error(...args)
}
