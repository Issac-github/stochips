import { useNavigate } from 'react-router'
import { Button } from '@renderer/components/ui/button'

const RootBoundary: React.FC = () => {
  const navigate = useNavigate()

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
          // location.reload()
          navigate('/')
        }}
      >
        Reload
      </Button>
    </div>
  )
}

export default RootBoundary
