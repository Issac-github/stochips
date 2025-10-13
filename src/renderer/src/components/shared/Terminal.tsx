import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'

const CustomTerminal: React.FC = () => {
  const divRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14
    })

    term.open(divRef.current!)
    term.write('What you want from \x1B[1;3;31mStochips\x1B[0m $ ')

    let currentLine = ''

    // 处理用户输入
    term.onData((data) => {
      const char = data.charCodeAt(0)

      if (char === 13) {
        // Enter 键
        term.write('\r\n')
        processCommand(currentLine.trim())
        currentLine = ''
        term.write('What you want from \x1B[1;3;31mStochips\x1B[0m $ ')
      } else if (char === 127) {
        // Backspace 键
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1)
          term.write('\b \b') // 删除字符
        }
      } else if (char >= 32) {
        // 可打印字符
        currentLine += data
        term.write(data) // 回显字符
      }
    })

    // 处理命令
    const processCommand = (command: string) => {
      if (command === '') return

      switch (command.toLowerCase()) {
        case 'help':
          term.write('Available commands:\r\n')
          term.write('  help    - Show this help\r\n')
          term.write('  clear   - Clear screen\r\n')
          term.write('  about   - About Stochips\r\n')
          term.write('  exit    - Close terminal\r\n')
          break
        case 'clear':
          term.clear()
          break
        case 'about':
          term.write('Stochips - Your data visualization platform\r\n')
          break
        case 'exit':
          term.write('Goodbye!\r\n')
          setTimeout(() => term.dispose(), 1000)
          break
        default:
          term.write(`Command not found: ${command}\r\n`)
          term.write('Type "help" for available commands\r\n')
      }
    }

    return () => {
      term.dispose()
    }
  }, [])

  return <div ref={divRef} className="h-full w-full" />
}

export default CustomTerminal
