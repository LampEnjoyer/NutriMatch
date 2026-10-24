import { BrowserRouter, Route, Routes } from 'react-router'

import { AppShell } from './components/AppShell'
import { DiscoverPage } from './pages/DiscoverPage'
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
          <Route
            path="today"
            element={
              <PlaceholderPage
                title="Today"
                description="Meals you log and your running totals for calories, protein, carbs and fat will appear here."
              />
            }
          />
          <Route
            path="grocery"
            element={
              <PlaceholderPage
                title="Grocery list"
                description="Pick recipes and their ingredients will be combined into one checklist here."
              />
            }
          />
          <Route
            path="settings"
            element={
              <PlaceholderPage
                title="Settings"
                description="Set optional nutrition targets, diets, allergies and ingredients to prefer or avoid."
              />
            }
          />
          <Route
            path="*"
            element={<PlaceholderPage title="Page not found" description="Check the address, or go back to Discover." />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
