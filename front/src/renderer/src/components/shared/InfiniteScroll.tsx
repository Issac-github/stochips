'use client'

import { FC, useId } from 'react'
import InfiniteScroll from 'react-infinite-scroll-component'
import type { Props as InfiniteScrollProps } from 'react-infinite-scroll-component'

interface Props extends Omit<InfiniteScrollProps, 'loader'> {
  componentId: string
  className?: string
  infiniteScrollClassName?: string
  loader?: React.ReactNode
}

const Loading = () => (
  <div className="text-muted-foreground mx-auto block p-4 text-center text-sm">
    Loading...
  </div>
)

export const InfiniteScrollFC: FC<Props> = ({
  componentId,
  className,
  infiniteScrollClassName,
  children,
  loader,
  ...restProps
}) => {
  const randomId = useId()
  const uniqueId = `${componentId}-${randomId}`

  return (
    <div
      className={`h-full overflow-x-hidden overflow-y-auto ${className}`}
      id={uniqueId}
    >
      <InfiniteScroll
        pullDownToRefreshContent={loader ? loader : <Loading />}
        releaseToRefreshContent={loader ? loader : <Loading />}
        loader={loader ? loader : <Loading />}
        pullDownToRefreshThreshold={50}
        scrollableTarget={uniqueId}
        className={infiniteScrollClassName}
        {...restProps}
      >
        {children}
      </InfiniteScroll>
    </div>
  )
}
