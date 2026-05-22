import { createContext, useContext, useState } from 'react'

const Ctx = createContext(null)

export function AppProvider({ children }) {
  const [user,       setUser]       = useState(null)      // { name, id, role? }
  const [client,    setClient]    = useState(null)      // { id, existing }
  const [report,     setReport]     = useState(null)      // full report object
  const [phqScore,   setPhqScore]   = useState(0)
  const [gadScore,   setGadScore]   = useState(0)

  return (
    <Ctx.Provider value={{
      user, setUser,
      client, setClient,
      report, setReport,
      phqScore, setPhqScore,
      gadScore, setGadScore,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export const useApp = () => useContext(Ctx)
