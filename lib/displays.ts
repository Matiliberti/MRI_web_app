// Each physical display (Raspberry Pi + screen) is fully independent: its own
// media table and its own row in pi_status / pi_settings. The web app picks a
// display by route; the Pi picks one via DISPLAY_ID in its .env.
//
// Display 1 maps onto the original single-display tables so the deployment
// that predates display 2 keeps working unchanged.

export interface DisplayConfig {
  /** Numeric id, also what the Pi sets as DISPLAY_ID. */
  id: number
  /** Label shown in the header. */
  name: string
  /** Route path where this display's controller lives. */
  path: string
  /** Table holding this display's feed. */
  mediaTable: string
  /** Row id in pi_status used for this display's heartbeat. */
  statusId: number
  /** Row id in pi_settings holding this display's volume. */
  settingsId: number
}

export const DISPLAYS: Record<number, DisplayConfig> = {
  1: {
    id: 1,
    name: 'Display 1',
    path: '/',
    mediaTable: 'display_media',
    statusId: 1,
    settingsId: 1,
  },
  2: {
    id: 2,
    name: 'Display 2',
    path: '/display-2',
    mediaTable: 'display_media_2',
    statusId: 2,
    settingsId: 2,
  },
}
