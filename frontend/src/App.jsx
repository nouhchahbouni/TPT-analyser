import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import Stores from './pages/Stores.jsx'
import Categories from './pages/Categories.jsx'
import Saved from './pages/Saved.jsx'
import Top50 from './pages/Top50.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/search" element={<Search />} />
        <Route path="/stores" element={<Stores />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/saved" element={<Saved />} />
        <Route path="/top50" element={<Top50 />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  )
}
