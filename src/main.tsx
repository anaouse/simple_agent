import { createRoot } from 'react-dom/client'
import App from '@/App'
import 'katex/dist/katex.min.css'
import '@/css/root.css'
import '@/css/home-page.css'
import '@/css/project-sidebar.css'
import '@/css/project-item.css'
import '@/css/message-area.css'
import '@/css/message-node.css'
import '@/css/input-box.css'
import '@/css/tailwind.css'

import 'katex/dist/katex.min.css'
import 'streamdown/styles.css'

createRoot(document.getElementById('root')!).render(<App />)
