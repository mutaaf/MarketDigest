import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Onboarding from './pages/Onboarding'
import Instruments from './pages/Instruments'
import Prompts from './pages/Prompts'
import DataSources from './pages/DataSources'
import DigestConfig from './pages/DigestConfig'
import RunPreview from './pages/RunPreview'
import Settings from './pages/Settings'
import Retrace from './pages/Retrace'
import ScoreCard from './pages/ScoreCard'
import OptionsFlow from './pages/OptionsFlow'

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/instruments" element={<Instruments />} />
        <Route path="/prompts" element={<Prompts />} />
        <Route path="/sources" element={<DataSources />} />
        <Route path="/digests" element={<DigestConfig />} />
        <Route path="/run" element={<RunPreview />} />
        <Route path="/retrace" element={<Retrace />} />
        <Route path="/scorecard" element={<ScoreCard />} />
        <Route path="/options" element={<OptionsFlow />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
