import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import heroImg from './assets/hero.png'
import './App.css'
import WorkerList from './components/WorkerList'
import MapView from './components/MapView'
import ComparisonView from './components/ComparisonView'

function App() {
  return (
    <div>
      <ComparisonView />
      <MapView />
      <WorkerList />
    </div>

  )
}

export default App
