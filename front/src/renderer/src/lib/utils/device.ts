import { errorLog } from '@shared/logger'

export const detectMacOs = () => {
  try {
    return window.navigator.userAgent.includes('Mac OS X')
  } catch (error) {
    errorLog(error)
    return false
  }
}
