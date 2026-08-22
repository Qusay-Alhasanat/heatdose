import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import WorkerList from './components/WorkerList'
import MapView from './components/MapView'

function App() {
  return (
    <div>
      <MapView />
      <WorkerList />
    </div>

  )
}

export default App
