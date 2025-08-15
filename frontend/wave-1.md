# Wave 1: React Fundamentals & Next.js Architecture

**Learning Objectives**: Master React hooks, component patterns, and Next.js App Router while building understanding through the DeepCuts codebase.

**Prerequisites**: Basic JavaScript knowledge, familiarity with HTML/CSS

**Time Commitment**: 4-6 hours

---

## 🎯 What You'll Learn

By the end of this wave, you'll understand:
- React functional components and modern hook patterns
- Next.js App Router architecture (Server vs Client components)
- TypeScript integration in React applications
- Component composition and prop drilling solutions
- Project structure for scalable React applications

---

## 💡 Concept Explained: React vs Traditional Web Development

**Traditional web development** required manually manipulating the DOM:
```javascript
// Old way - Direct DOM manipulation
document.getElementById('counter').innerHTML = count;
document.addEventListener('click', function() {
  count++;
  document.getElementById('counter').innerHTML = count;
});
```

**React's approach** - Declare what you want, React handles the how:
```tsx
// React way - Declarative
function Counter() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <span>{count}</span>
      <button onClick={() => setCount(count + 1)}>+</button>
    </div>
  );
}
```

**Real-world analogy**: Traditional DOM manipulation is like giving step-by-step directions to someone. React is like saying "I want to be at the mall" and letting GPS figure out the best route.

---

## 🏗️ Project Structure Analysis

Let's examine how this Next.js application is organized:

```
src/
├── app/                    # Next.js 13+ App Router
│   ├── components/         # Reusable UI components
│   ├── contexts/          # React Context providers
│   ├── favorites/         # Favorites page route
│   └── page.tsx          # Home page (root route)
├── lib/                   # Utility libraries  
└── styles/               # Global styles
```

### **💡 Concept Explained: App Router vs Pages Router**

**Next.js App Router** (new, what this project uses):
- File-system based routing inside `app/` directory
- Co-located layouts, loading, and error states
- Server and Client Components by default
- Built-in support for React Server Components

**Pages Router** (legacy):
- Routes defined in `pages/` directory  
- All components are client-side by default
- Separate `_app.js` and `_document.js` files

**Why App Router is better**: Better performance (server rendering by default), improved developer experience, and more granular control over rendering.

---

## 🔍 Deep Dive: Component Analysis

Let's study the `AlbumCard` component to understand modern React patterns:

### **Component Interface Design**

```tsx
// File: src/app/components/AlbumCard.tsx
interface AlbumCardProps {
  album: AlbumData;
  onListenNow: (album: AlbumData) => void;
  onToggleFavorite?: (album: AlbumData) => void;
  isFavorited?: boolean;
  isLoading?: boolean;
}
```

**💡 Concept Explained: Props Interface**

Props are like function parameters - they're data passed from parent to child components. TypeScript interfaces define exactly what data structure is expected, catching errors at development time rather than runtime.

**Benefits of well-defined interfaces**:
- **Autocomplete**: Your editor knows what props are available
- **Error catching**: TypeScript warns if you pass wrong data types
- **Documentation**: Other developers understand component requirements
- **Refactoring safety**: Changes to interfaces highlight all affected code

### **Event Handling Patterns**

```tsx
const handleFavoriteClick = (e: React.MouseEvent) => {
  e.stopPropagation(); // Prevent parent click events
  if (onToggleFavorite && !isLoading) {
    onToggleFavorite(album);
  }
};
```

**💡 Concept Explained: Event Propagation**

When you click a button inside a card, both the button AND the card might handle the click. `stopPropagation()` prevents the event from "bubbling up" to parent elements.

**Real-world analogy**: Like interrupting someone in a meeting - you handle their question immediately instead of letting them continue talking to the boss.

### **Conditional Rendering Patterns**

```tsx
{album.cover_url ? (
  <img 
    className="cover-image" 
    src={album.cover_url} 
    alt={`${album.title} cover`}
    onError={(e) => {
      const target = e.target as HTMLImageElement;
      target.style.display = 'none';
      const placeholder = target.nextElementSibling as HTMLElement;
      if (placeholder) placeholder.style.display = 'flex';
    }}
  />
) : null}
```

**🔍 Deep Dive: Graceful Fallbacks**

This code implements a **progressive enhancement** pattern:
1. **Try to show album cover** (best experience)
2. **If image fails to load**, hide it and show placeholder
3. **Always provide accessible alt text** for screen readers

This is superior to simply showing a broken image icon because it maintains visual consistency and provides clear feedback about missing content.

---

## 📱 Understanding Next.js App Router

### **Server vs Client Components**

The main page (`src/app/page.tsx`) starts with:
```tsx
'use client';
```

**💡 Concept Explained: The 'use client' Directive**

By default, Next.js 13+ components are **Server Components** - they run on the server during build/request time. Adding `'use client'` makes them **Client Components** - they run in the browser.

**When to use Client Components**:
- Interactive features (onClick, form handling)
- Browser APIs (localStorage, geolocation)
- React hooks (useState, useEffect)
- Real-time features

**When to use Server Components**:
- Static content rendering
- Database queries
- Server-only operations
- Better performance for non-interactive content

### **File-Based Routing**

```
app/
├── page.tsx              # Homepage (/)
├── favorites/
│   └── page.tsx         # Favorites page (/favorites)
└── auth/
    └── callback/
        └── page.tsx     # Auth callback (/auth/callback)
```

**Advantages over manual routing**:
- **No configuration needed** - files automatically become routes
- **Code splitting** - each page is a separate JavaScript bundle
- **Lazy loading** - pages only load when visited

---

## 🎣 React Hooks Deep Dive

Let's analyze the hooks usage in the main page component:

### **useState for Component State**

```tsx
const [albums, setAlbums] = useState<AlbumData[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);
```

**💡 Concept Explained: State Management Levels**

React applications have different levels of state:

1. **Component State** (useState): Data only this component needs
2. **Lifted State**: Data shared between sibling components  
3. **Context State**: Data many unrelated components need
4. **External State**: Data managed by external libraries

**Rule of thumb**: Start with component state, lift only when necessary.

### **useEffect for Side Effects**

```tsx
useEffect(() => {
  if (!initialLoadDone && !searchQuery) {
    loadInitialAlbums();
    setInitialLoadDone(true);
  }
}, [initialLoadDone, searchQuery, loadInitialAlbums]);
```

**🔍 Deep Dive: Dependency Arrays**

The dependency array `[initialLoadDone, searchQuery, loadInitialAlbums]` tells React when to re-run this effect:

- **Empty array `[]`**: Run once on component mount
- **No array**: Run on every render (usually wrong!)
- **With dependencies**: Run when any dependency changes

**Common mistake**: Forgetting to include all dependencies leads to stale closures and bugs.

### **useCallback for Performance**

```tsx
const handleSearch = useCallback(async (query: string) => {
  // Search logic
}, [searchCache]);
```

**💡 Concept Explained: When to Use useCallback**

`useCallback` memoizes a function - returns the same function reference unless dependencies change.

**Use it when**:
- Function is passed to child components as props
- Function is used in other hook dependencies
- Creating expensive functions that cause unnecessary re-renders

**Don't use it** for simple event handlers that don't cause performance issues.

---

## 🧩 Component Composition Patterns

### **Props vs Children Pattern**

```tsx
// Props pattern - explicit data passing
<AlbumCard 
  album={album} 
  onListenNow={handleListenNow}
  onToggleFavorite={handleToggleFavorite}
  isFavorited={favoriteAlbums.has(album.id)}
/>

// Children pattern - flexible content
<AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)}>
  <LoginForm />
</AuthModal>
```

**When to use props**: When parent controls specific behavior
**When to use children**: When child content varies but wrapper behavior is consistent

### **Compound Components Pattern**

While not used in this specific codebase, it's worth understanding:

```tsx
// Instead of one monolithic component
<ComplexForm 
  showTitle={true} 
  showDescription={true} 
  showSubmitButton={true} 
  titleText="My Form"
/>

// Compound components for flexibility
<Form>
  <Form.Title>My Form</Form.Title>
  <Form.Description>Please fill out...</Form.Description>
  <Form.Fields>
    {/* form content */}
  </Form.Fields>
  <Form.Submit>Save</Form.Submit>
</Form>
```

---

## 🔧 TypeScript Integration Patterns

### **Interface vs Type**

```tsx
// Interface - extensible, for object shapes
interface AlbumCardProps {
  album: AlbumData;
  onListenNow: (album: AlbumData) => void;
}

// Type - for unions, primitives, computed types
type LoadingState = 'idle' | 'loading' | 'success' | 'error';
type AlbumWithFavorite = AlbumData & { isFavorited: boolean };
```

**💡 Concept Explained: When to Use Each**

- **Interfaces**: Object structures, especially for React props and API responses
- **Types**: Union types, mapped types, and computed types

### **Generic Types in Hooks**

```tsx
const [albums, setAlbums] = useState<AlbumData[]>([]);
//                          ^^^^^^^^^^^^ Generic type parameter
```

This tells TypeScript that `albums` is an array of `AlbumData` objects, enabling:
- **Autocomplete** when accessing album properties
- **Type checking** when adding items to the array
- **Error prevention** when passing data to other functions

---

## 🎨 Styling Architecture

### **SCSS Module Pattern**

```scss
// AlbumCard.scss
.album-card {
  display: flex;
  flex-direction: column;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  .album-title {
    font-weight: 600;
  }
}
```

**Benefits of SCSS**:
- **Variables**: Consistent colors and sizes across app
- **Nesting**: Styles mirror HTML structure
- **Mixins**: Reusable style patterns
- **Calculations**: Dynamic values based on other values

### **CSS-in-JS vs CSS Modules vs Global CSS**

This project uses **global SCSS** with **component-specific stylesheets**:

**Pros**:
- Simple mental model
- Easy to debug in browser
- Familiar CSS syntax
- Good performance

**Cons**:
- Risk of naming conflicts
- Harder to enforce design system
- No dynamic styling based on JS state

**Alternative approaches**:
- **CSS Modules**: Automated scoping (`styles.title`)
- **CSS-in-JS**: Dynamic styles based on props (Styled Components, Emotion)
- **Utility CSS**: Pre-built classes (Tailwind CSS)

---

## 🛠️ Practical Exercises

### **Exercise 1: Add Loading States**

Currently, album cards show basic loading indicators. Enhance this by adding skeleton loading states:

1. Create a `SkeletonCard` component that mimics the album card layout
2. Show skeleton cards while data is loading
3. Animate the skeleton with a subtle shimmer effect

```tsx
// Starter code
function SkeletonCard() {
  return (
    <div className="album-card skeleton">
      <div className="skeleton-image" />
      <div className="skeleton-text" />
      <div className="skeleton-text short" />
    </div>
  );
}
```

### **Exercise 2: Custom Hook Extraction**

Extract the favorite toggle logic into a custom hook:

```tsx
// Create this custom hook
function useFavoriteToggle() {
  // Move favorite-related state and logic here
  // Return an object with state and handlers
}

// Use it in the main component
function Home() {
  const { favoriteAlbums, handleToggleFavorite, loadUserFavorites } = useFavoriteToggle();
  // ... rest of component
}
```

### **Exercise 3: Error Boundaries**

Add error boundaries to gracefully handle component crashes:

```tsx
class AlbumCardErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return <div>Something went wrong with this album card.</div>;
    }
    return this.props.children;
  }
}
```

---

## 🔍 Common Patterns & Anti-Patterns

### **✅ Good Patterns**

```tsx
// 1. Proper dependency arrays
useEffect(() => {
  fetchData();
}, [userId]); // Re-run when userId changes

// 2. Early returns for readability
if (loading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} />;

// 3. Consistent naming
const [isLoading, setIsLoading] = useState(false);
const handleSubmit = (e) => { /* ... */ };
```

### **❌ Anti-Patterns to Avoid**

```tsx
// 1. Missing dependency arrays (causes infinite loops)
useEffect(() => {
  setData(fetchData());
}); // No dependency array!

// 2. Mutating state directly
albums.push(newAlbum); // Don't do this
setAlbums([...albums, newAlbum]); // Do this instead

// 3. Too many state variables
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
const [success, setSuccess] = useState(false);
// Better: use a single state object or useReducer
```

---

## 🎯 Key Takeaways

1. **React is declarative** - describe what you want, not how to achieve it
2. **Components should be focused** - each component should have a single responsibility  
3. **Props flow down, events flow up** - parent components manage state, children report events
4. **TypeScript catches errors early** - invest time in good type definitions
5. **Hooks have rules** - always call them at the top level, include all dependencies
6. **Next.js App Router is powerful** - leverage server/client components appropriately

---

## 🚀 Next Steps

Ready for Wave 2? You'll dive deep into authentication systems, learning how JWT tokens work, how Supabase manages user sessions, and how to implement secure authentication flows in React applications.

**Coming up in Wave 2**:
- JWT token lifecycle and security
- Supabase authentication integration  
- Session management across browser tabs
- Protected routes and conditional rendering
- Error handling for authentication failures

---

## 📚 Additional Resources

- **[React Beta Docs](https://react.dev)** - Latest React documentation with hooks focus
- **[Next.js App Router Guide](https://nextjs.org/docs/app)** - Official App Router documentation  
- **[TypeScript + React Guide](https://github.com/typescript-cheatsheets/react)** - Community TypeScript patterns
- **[React Patterns](https://reactpatterns.com/)** - Common React component patterns