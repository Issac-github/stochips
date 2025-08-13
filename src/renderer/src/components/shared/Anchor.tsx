import { FC, useRef, useState } from 'react'
import { Anchor } from 'antd'

interface Props {
  anchorList: { title: string; key: string; href: string }[]
  content: React.ReactNode
  anchorStyleProps?: Record<string, string>
  contentStyleProps?: Record<string, string>
  afterLink?: (category: string) => void
}

// eslint-disable-next-line react-refresh/only-export-components
const StoAnchor: FC<Props> = ({
  anchorList,
  content,
  anchorStyleProps = {},
  contentStyleProps = {},
  afterLink
}) => {
  const anchorRef = useRef<HTMLDivElement | null>(null)
  const contentRef = useRef<HTMLOListElement | null>(null)
  const [currentAnchor, setCurrentAnchor] = useState<string>(
    anchorList[0]?.href
  )
  const clickAnchor = (href: string) => {
    setCurrentAnchor(href)
    const index = anchorList.findIndex((item) => item.href === href)
    contentRef.current?.children?.[index].scrollIntoView({ behavior: 'smooth' })
  }

  const handleScroll = () => {
    if (!anchorRef.current || !contentRef.current) {
      return
    }
    const anchorDom = anchorRef.current
    const contentDom = contentRef.current
    const parentRect = anchorDom.getBoundingClientRect()
    const children = contentDom.children
    const index = Array.from(children).findIndex((child) => {
      const childRect = child.getBoundingClientRect()
      return Math.ceil(childRect.top) >= parentRect.top
    })
    if (children?.[index]) {
      setCurrentAnchor(anchorList?.[index]?.href)
    }
    if (
      contentDom.scrollTop + contentDom.clientHeight + 12 >
      contentDom.scrollHeight
    ) {
      setCurrentAnchor(anchorList[anchorList.length - 1].href)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        gap: '16px',
        ...anchorStyleProps
      }}
      ref={anchorRef}
    >
      <Anchor
        onClick={(e, link) => {
          e.preventDefault()
          clickAnchor(link.href)
          afterLink?.(link.href)
        }}
        getCurrentAnchor={() => currentAnchor}
        items={anchorList}
      />
      <ol
        ref={contentRef}
        style={{
          overflow: 'auto',
          padding: '12px 0',
          ...contentStyleProps
        }}
        onScroll={handleScroll}
      >
        {content}
      </ol>
    </div>
  )
}

const useStoAnchor = ({
  anchorList,
  anchorStyleProps,
  contentStyleProps,
  content,
  afterLink
}: Props) => {
  const anchor = (
    <StoAnchor
      anchorList={anchorList}
      anchorStyleProps={anchorStyleProps}
      content={content}
      contentStyleProps={contentStyleProps}
      afterLink={afterLink}
    />
  )
  return {
    anchor
  }
}

export default useStoAnchor
