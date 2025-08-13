import { Button } from 'antd'

const RootBoundary: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh'
      }}
    >
      <Button
        onClick={() => {
          location.reload()
        }}
      >
        Reload
      </Button>
    </div>
  )
}

export default RootBoundary
