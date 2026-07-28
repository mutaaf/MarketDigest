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
import SignalTerminal from './pages/SignalTerminal'
import RiskDashboard from './pages/RiskDashboard'
import PaperTrading from './pages/PaperTrading'
import Backtesting from './pages/Backtesting'
import PineScripts from './pages/PineScripts'
import InnovationDashboard from './pages/InnovationDashboard'
import CompassLayout from './components/compass/CompassLayout'
import CompassHome from './pages/CompassHome'
import CompassPortfolio from './pages/CompassPortfolio'
import CompassIdeas from './pages/CompassIdeas'
import CompassCompare from './pages/CompassCompare'
import CompassWatchlist from './pages/CompassWatchlist'
import CompassRetire from './pages/CompassRetire'
import CompassAsk from './pages/CompassAsk'
import CompassLearn from './pages/CompassLearn'

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<Layout />}>
        <Route path="/" element={<SignalTerminal />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/risk" element={<RiskDashboard />} />
        <Route path="/paper" element={<PaperTrading />} />
        <Route path="/backtest" element={<Backtesting />} />
        <Route path="/pine" element={<PineScripts />} />
        <Route path="/innovation" element={<InnovationDashboard />} />
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
      <Route path="/compass" element={<CompassLayout />}>
        <Route index element={<CompassHome />} />
        <Route path="portfolio" element={<CompassPortfolio />} />
        <Route path="ideas" element={<CompassIdeas />} />
        <Route path="compare" element={<CompassCompare />} />
        <Route path="watchlist" element={<CompassWatchlist />} />
        <Route path="retire" element={<CompassRetire />} />
        <Route path="ask" element={<CompassAsk />} />
        <Route path="learn" element={<CompassLearn />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
