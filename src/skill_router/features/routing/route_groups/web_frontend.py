"""Web Frontend route definitions."""

from ..route import Route

WEB_FRONTEND_ROUTES: list[Route] = [
    Route(
        patterns=('\\b(payload|payloadcms|payload cms|payload\\.config|collectionconfig)\\b',
         '\\b(collections?|fields?|hooks?|access control)\\b.*\\b(payload|cms)\\b'),
        hint=('Skill: load `payload` for Payload CMS 3.x configs, collections, fields, hooks, access control, '
         'Local API security, transactions, plugins, and Next.js integration.'),
        skills=('payload',),
        doc_namespaces=('payload', 'nextjs'),
    ),
    Route(
        patterns=('\\b(jenkins|jenkinsfile|jcasc|job dsl)\\b',
         '\\b(declarative pipeline|scripted pipeline|shared librar(?:y|ies))\\b'),
        hint=('Skill: load `jenkins` for Jenkinsfile, Declarative/Scripted Pipeline, shared libraries, JCasC, '
         'credentials safety, agents, plugins, and CI/CD troubleshooting.'),
        skills=('jenkins',),
        doc_namespaces=('jenkins',),
    ),
    Route(
        patterns=('\\b(ag[- ]?grid|data grid|angular grid|celdas?|grid community)\\b',
         '\\b(row group|tree data|master detail|excel export|cell renderer)\\b.*\\b(ag[- ]?grid|grid)\\b'),
        hint=('Skill: load `ag-grid-community-angular` for AG Grid Community (free) patterns in Angular — setup '
         'v34+, themes, cell renderers, infinite scroll, and workarounds for tree-data, grouping, '
         'master/detail, Excel export, and clipboard without Enterprise license.'),
        skills=('ag-grid-community-angular',),
        doc_namespaces=('ag-grid',),
    ),
    Route(
        patterns=('\\b(react|reactjs|\\bjsx\\b|\\btsx\\b|next\\.?js|nextjs|server '
         'components?\\b|usestate|useeffect|usememo|react compiler|use action state)\\b',),
        hint=('Skill: load `react` for React 19 (hooks, Server Components, Actions, React Compiler, state, '
         'Next.js App Router); `frontend-design` for UI craft; `typescript-pro` for typed JSX.'),
        skills=('react', 'frontend-design', 'typescript-pro'),
        tools=('context7',),
        doc_namespaces=('react', 'nextjs'),
        priority=75,
    ),
    Route(
        patterns=('\\b(angular|ngfor|ngif|@component|@injectable|rxjs|signals?\\b|angular cli|ng serve|ng '
         'build|standalone component|inject\\(\\)|providezoneless)\\b',),
        hint=('Skill: load `angular` for current Angular v22+ (standalone components, signals, zoneless, control '
         'flow @if/@for, inject(), RxJS, CLI); `frontend-design` for UI craft; `typescript-pro` for typed '
         'templates.'),
        skills=('angular', 'frontend-design', 'typescript-pro'),
        tools=('context7',),
        doc_namespaces=('angular', 'rxjs'),
        priority=75,
    ),
    Route(
        patterns=('\\b(vue|vuejs|vue\\.js|script setup|composition '
         'api|composables?\\b|pinia|nuxt|defineprops|defineemits)\\b',),
        hint=('Skill: load `vue` for Vue 3.5 (Composition API, <script setup>, ref/reactive/computed/watch, '
         'composables, Pinia, Nuxt); `frontend-design` for UI craft.'),
        skills=('vue', 'frontend-design'),
        tools=('context7',),
        doc_namespaces=('vue', 'nuxt'),
    ),
    Route(
        patterns=('\\b(svelte|sveltekit|runes|\\$state|\\$derived|\\$effect)\\b',),
        hint=('Skill: load `svelte` for Svelte 5 runes ($state/$derived/$effect, onclick, $props) + SvelteKit '
         '(load/form actions/SSR); `frontend-design` for UI craft.'),
        skills=('svelte', 'frontend-design'),
        tools=('context7',),
        doc_namespaces=('svelte', 'sveltekit'),
    ),
    Route(
        patterns=('\\b(tailwind|tailwindcss|utility[- ]first|@theme|@apply|\\btw-)\\b',),
        hint=('Skill: load `tailwind` for Tailwind v4 (Oxide, CSS-first @theme config, responsive/container '
         'variants, @apply discipline); `css` for the language; `ux-ui` for token theory.'),
        skills=('tailwind', 'css', 'ux-ui'),
        tools=('context7',),
        doc_namespaces=('tailwind',),
    ),
    Route(
        patterns=('\\b(good interface|responsive layout|adaptive design|component architecture|web vitals|core web '
         'vitals|\\blcp\\b|\\binp\\b|\\bcls\\b|design system in code|progressive enhancement|frontend '
         'design|semantic html|html form|css layout|flexbox|css grid)\\b',
         '\\b(diseño|interfaz|interfaces de usuario|buena interfaz|c[oó]mo dise[ñn]ar|componente '
         'visual|layout)\\b'),
        hint=('Skill: load `frontend-design` for the craft of building good interfaces (component thinking, '
         'responsive/layout, design-system-in-code, web vitals, a11y) — framework-agnostic. Bases: '
         'html+css+javascript-pro; load `react`/`angular`/`vue`/`svelte` when the framework is known.'),
        skills=('frontend-design', 'html', 'css', 'javascript-pro'),
        priority=70,
    ),
    Route(
        patterns=('\\b(figma|pixel[- ]?perfect|dise[nñ]o figma|sync design|visual discrepancy|compara con '
         'figma|pantallazo|screenshot comparison|design fidelity)\\b',),
        hint=('Skill: load `figma-design-sync` or load `design-implementation-reviewer` or load '
         '`design-iterator` to compare, sync, and iteratively refine live web UI implementations against '
         'Figma designs.'),
        skills=('figma-design-sync', 'design-implementation-reviewer', 'design-iterator'),
    ),
]
