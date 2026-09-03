import type { Metadata } from 'next'
import DisplayApp from '@/components/DisplayApp'
import { DISPLAYS } from '@/lib/displays'

export const metadata: Metadata = { title: 'MRI Display 2' }

export default function Display2Page() {
  return <DisplayApp display={DISPLAYS[2]} />
}
