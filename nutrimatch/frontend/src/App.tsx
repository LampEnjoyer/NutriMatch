import { BrowserRouter, Route, Routes } from 'react-router'

import { AppShell } from './components/AppShell'
import { DiscoverPage } from './pages/DiscoverPage'
import { GroceryPage } from './pages/GroceryPage'
import { PlaceholderPage } from './pages/PlaceholderPage'
import { RecipePage } from './pages/RecipePage'
import { SavedPage } from './pages/SavedPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<DiscoverPage />} />
          <Route path="recipes/:recipeId" element={<RecipePage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="grocery" element={<GroceryPage />} />
          <Route
            path="*"
            element={<PlaceholderPage title="Page not found" description="Check the address, or go back to Discover." />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
