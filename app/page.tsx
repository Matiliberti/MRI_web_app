import DisplayApp from '@/components/DisplayApp'
import { DISPLAYS } from '@/lib/displays'

export default function Display1Page() {
  return <DisplayApp display={DISPLAYS[1]} />
}
