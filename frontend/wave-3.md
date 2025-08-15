# Wave 3: API Integration & Progressive Loading

**Learning Objectives**: Master modern API integration patterns, implement progressive data loading, and understand advanced state management techniques for real-world applications.

**Prerequisites**: Wave 1 & 2 completed, understanding of async JavaScript and authentication

**Time Commitment**: 6-8 hours

---

## 🎯 What You'll Learn

By the end of this wave, you'll understand:
- API client architecture and centralized request handling
- Progressive loading patterns for enhanced user experience
- Caching strategies for performance optimization
- Error handling and retry mechanisms
- State management patterns beyond basic useState
- Real-time data synchronization techniques

---

## 💡 Concept Explained: Traditional vs Modern API Integration

**Traditional approach** (jQuery era):
```javascript
// Scattered API calls throughout components
$.ajax({
  url: '/api/albums',
  success: function(data) { $('#results').html(data); },
  error: function() { alert('Error!'); }
});
```

**Modern approach** (what this app demonstrates):
```typescript
// Centralized API client with consistent patterns
class ApiClient {
  private baseURL = process.env.NEXT_PUBLIC_API_URL;
  
  async searchAlbums(query: string): Promise<SearchResponse> {
    const response = await this.request('/api/v1/search', {
      method: 'POST',
      body: JSON.stringify({ query })
    });
    return response.json();
  }
}
```

**Benefits of modern approach**:
- **Consistency**: All API calls follow same patterns
- **Maintainability**: Changes in one place affect all requests
- **Type safety**: TypeScript interfaces for all responses
- **Error handling**: Centralized error processing
- **Authentication**: Automatic token injection

---

## 🏗️ API Client Architecture

Let's analyze the centralized API client pattern used in this application:

### **Client Class Structure**

```typescript
// File: src/lib/api.ts
class ApiClient {
  // Single source of truth for backend communication
  
  private async getAuthHeaders(): Promise<HeadersInit> {
    // Centralized authentication header management
  }
  
  async searchAlbums(query: string) {
    // Specific API operations with consistent error handling
  }
}

export const apiClient = new ApiClient();
```

**🔍 Deep Dive: Singleton Pattern**

The API client uses the **Singleton pattern** - one instance shared across the entire app:

**Benefits**:
- **Consistent configuration**: Base URL, headers, timeouts
- **Shared caching**: Request results cached across components
- **Connection pooling**: HTTP connections reused efficiently
- **Centralized logging**: All API interactions logged consistently

**Alternative patterns**:
- **Factory pattern**: Create new client instances with different configs
- **Functional approach**: Standalone functions instead of class methods
- **Hook-based**: Custom hooks that encapsulate API logic

### **Request Interceptors and Headers**

```typescript
private async getAuthHeaders(): Promise<HeadersInit> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };

  try {
    const { supabase } = await import('@/lib/supabase');
    const { data: { session }, error } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }
  } catch (error) {
    console.error('Error getting auth headers:', error);
  }
  
  return headers;
}
```

**💡 Concept Explained: Request Interceptors**

**What they do**: Automatically modify every request before it's sent
**Common uses**:
- **Authentication**: Add JWT tokens to headers
- **Content-Type**: Set appropriate media types
- **Correlation IDs**: Add request tracking
- **User-Agent**: Identify client application

**Response interceptors** (not shown, but commonly used):
- **Error transformation**: Convert HTTP errors to app-specific errors
- **Data transformation**: Normalize response formats
- **Caching**: Store responses for future use
- **Analytics**: Track API usage patterns

---

## 🔄 Progressive Loading Patterns

One of the most sophisticated aspects of this application is its progressive loading implementation:

### **Basic Content First, Enhanced Data Later**

```typescript
const handleSearch = useCallback(async (query: string) => {
  // 1. Show AI recommendations immediately (fast)
  const searchData: SearchResponse = await apiClient.searchAlbums(query);
  
  if (searchData.recommendations && searchData.recommendations.length > 0) {
    setAlbums(searchData.recommendations); // Show basic data
    setLoading(false);
    
    // 2. Load Spotify/Discogs data progressively (slower but richer)
    loadSpotifyDataProgressively(searchData.recommendations, cacheKey);
  }
}, [searchCache]);
```

**💡 Concept Explained: Progressive Enhancement Strategy**

**Layer 1 - Core Content** (loads in ~2-3 seconds):
- AI-generated album recommendations
- Basic metadata (title, artist, genre, year)
- Immediate user value

**Layer 2 - Enhanced Content** (loads in background):
- Spotify preview URLs for listening
- High-quality album artwork
- Discogs metadata and purchase links
- Social features enhancement

**Real-world analogy**: Like a newspaper - you can read the headlines immediately, then photos and detailed articles load as you scroll.

### **Parallel Data Enrichment**

```typescript
const loadSpotifyDataProgressively = async (initialAlbums: AlbumData[], cacheKey: string) => {
  // Load Spotify data for each album in parallel
  const promises = initialAlbums.map(async (album) => {
    try {
      const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
      
      const enrichedAlbum = {
        ...album,
        spotify_preview_url: spotifyData.spotify_preview_url,
        spotify_url: spotifyData.spotify_url,
        cover_url: spotifyData.cover_url || album.cover_url,
        discogs_url: spotifyData.discogs_url || album.discogs_url
      };
      
      // Update UI immediately when each album's data arrives
      setAlbums(currentAlbums => 
        currentAlbums.map(a => 
          a.id === album.id ? enrichedAlbum : a
        )
      );
    } catch (error) {
      console.error(`Failed to load Spotify data for ${album.title}:`, error);
      // Gracefully continue with other albums
    }
  });
  
  await Promise.all(promises);
};
```

**🔍 Deep Dive: Parallel vs Sequential Loading**

**Sequential loading** (traditional):
```typescript
for (const album of albums) {
  const data = await fetchSpotifyData(album);
  updateAlbum(album.id, data);
}
// Takes: 3 seconds × 10 albums = 30 seconds total
```

**Parallel loading** (this app):
```typescript
const promises = albums.map(album => fetchSpotifyData(album));
await Promise.all(promises);
// Takes: max(3 seconds for any single album) = ~3 seconds total
```

**Benefits of parallel loading**:
- **Faster completion**: All requests happen simultaneously  
- **Better UX**: UI updates as each item completes
- **Resource efficiency**: Better utilization of network capacity
- **Fault tolerance**: One failure doesn't block others

---

## 💾 Caching Strategies

The application implements multiple caching layers for optimal performance:

### **In-Memory Request Caching**

```typescript
const [searchCache, setSearchCache] = useState<Map<string, AlbumData[]>>(new Map());

const handleSearch = useCallback(async (query: string) => {
  // Check cache first
  const cacheKey = query.toLowerCase().trim();
  if (searchCache.has(cacheKey)) {
    setAlbums(searchCache.get(cacheKey) || []);
    return; // Skip API call entirely
  }
  
  // Make API call and cache results
  const searchData = await apiClient.searchAlbums(query);
  setSearchCache(prev => new Map(prev.set(cacheKey, searchData.recommendations)));
}, [searchCache]);
```

**💡 Concept Explained: Caching Levels**

**L1 - Component Memory** (this app):
- **Lifetime**: Component unmount or browser refresh
- **Speed**: Instant (no network)  
- **Storage**: JavaScript Map/Set objects
- **Use case**: Same session repeated searches

**L2 - Browser Storage**:
- **Lifetime**: User-controlled (localStorage) or tab-controlled (sessionStorage)
- **Speed**: Very fast (disk read)
- **Storage**: Key-value strings
- **Use case**: Cross-session data persistence

**L3 - HTTP Cache**:
- **Lifetime**: Server-controlled via Cache-Control headers
- **Speed**: Fast (no server processing)
- **Storage**: Browser HTTP cache
- **Use case**: Static assets and API responses

**L4 - CDN Cache**:
- **Lifetime**: Server-controlled
- **Speed**: Fast (geographically distributed)
- **Storage**: Edge servers worldwide
- **Use case**: Global content distribution

### **Intelligent Cache Invalidation**

```typescript
// Update cache with enriched results after progressive loading
setAlbums(currentAlbums => {
  setSearchCache(prev => new Map(prev.set(cacheKey, currentAlbums)));
  return currentAlbums;
});
```

**Cache invalidation strategies**:
- **Time-based**: Expire after X minutes
- **Event-based**: Clear when user logs out
- **Version-based**: Include API version in cache key
- **Dependency-based**: Clear related data when user changes

---

## 🚨 Error Handling & Recovery

### **Graceful Degradation Patterns**

```typescript
async getRandomAlbums(limit: number = 10): Promise<{albums: AlbumData[], total: number}> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    
    const response = await fetch(`${API_BASE_URL}/api/v1/albums/random?limit=${sanitizedLimit}`, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    // Graceful fallback - app continues to work
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        console.warn('Random albums request timed out');
        return { albums: [], total: 0 };
      }
      if (error.message === 'Failed to fetch') {
        console.warn('Failed to connect to backend server');
        return { albums: [], total: 0 };
      }
    }
    console.error('Get random albums error:', error);
    return { albums: [], total: 0 };
  }
}
```

**🔍 Deep Dive: Error Classification & Handling**

**Network Errors**:
- **AbortError**: Request was cancelled (timeout)
- **TypeError**: Network connectivity issues
- **Response**: Return empty data, show offline message

**HTTP Errors**:
- **400-499**: Client errors (bad request, unauthorized)
- **500-599**: Server errors (internal error, service unavailable)  
- **Response**: Show specific error message, provide retry option

**Application Errors**:
- **Validation errors**: Invalid input format
- **Business logic errors**: Resource not found
- **Response**: Show user-friendly message, suggest corrections

### **Request Timeout and Retry Logic**

```typescript
// Timeout implementation
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 15000);

// Conceptual retry logic (not implemented in this app)
async function withRetry<T>(
  operation: () => Promise<T>, 
  maxAttempts: number = 3
): Promise<T> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      if (attempt === maxAttempts || !isRetryableError(error)) {
        throw error;
      }
      
      // Exponential backoff: 1s, 2s, 4s, 8s...
      const delay = Math.pow(2, attempt) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}
```

**💡 Concept Explained: Retry Strategies**

**Linear backoff**: 1s, 1s, 1s, 1s (can overwhelm failing servers)
**Exponential backoff**: 1s, 2s, 4s, 8s (gradually reduces load)  
**Exponential with jitter**: Add randomness to prevent thundering herd

**When to retry**:
- ✅ Network timeouts
- ✅ 503 Service Unavailable  
- ✅ 429 Too Many Requests
- ❌ 400 Bad Request
- ❌ 401 Unauthorized
- ❌ 404 Not Found

---

## 🎛️ Advanced State Management Patterns

### **State Synchronization Across Components**

```typescript
// Update both main album list and selected album details
setAlbums(currentAlbums => 
  currentAlbums.map(a => 
    a.id === album.id ? enrichedAlbum : a
  )
);

setSelectedAlbum(current => 
  current && current.id === album.id ? enrichedAlbum : current
);
```

**State synchronization challenges**:
- **Multiple representations**: Same data shown in different components
- **Partial updates**: Some components need subset of data
- **Timing issues**: Updates might arrive out of order
- **Memory leaks**: Forgetting to clean up subscriptions

### **Custom Hooks for State Logic**

```typescript
// Conceptual custom hook extraction
function useAlbumData() {
  const [albums, setAlbums] = useState<AlbumData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const searchAlbums = useCallback(async (query: string) => {
    // Search logic
  }, []);
  
  const loadSpotifyData = useCallback(async (albums: AlbumData[]) => {
    // Progressive loading logic
  }, []);
  
  return {
    albums,
    loading,
    error,
    searchAlbums,
    loadSpotifyData
  };
}
```

**Benefits of custom hooks**:
- **Reusability**: Same logic across multiple components
- **Testability**: Hooks can be tested in isolation
- **Separation of concerns**: UI vs business logic
- **Composition**: Combine multiple hooks for complex behavior

### **State Machines for Complex Flows**

```typescript
// Conceptual state machine for search flow
type SearchState = 
  | { status: 'idle' }
  | { status: 'searching', query: string }
  | { status: 'enriching', albums: AlbumData[] }
  | { status: 'complete', albums: AlbumData[] }
  | { status: 'error', error: string };

function searchReducer(state: SearchState, action: SearchAction): SearchState {
  switch (action.type) {
    case 'START_SEARCH':
      return { status: 'searching', query: action.query };
    case 'BASIC_RESULTS':
      return { status: 'enriching', albums: action.albums };
    case 'ENRICHMENT_COMPLETE':
      return { status: 'complete', albums: action.albums };
    case 'ERROR':
      return { status: 'error', error: action.error };
    default:
      return state;
  }
}
```

**Why state machines matter**:
- **Predictable behavior**: Impossible states are prevented
- **Clear transitions**: Explicit rules for state changes
- **Debugging**: Easy to trace state history
- **Testing**: Well-defined inputs and outputs

---

## 🔄 Real-time Data Patterns

### **Optimistic Updates**

```typescript
const handleToggleFavorite = async (album: AlbumData) => {
  const isFavorited = favoriteAlbums.has(album.id);
  
  // 1. Optimistic update - assume success
  if (isFavorited) {
    setFavoriteAlbums(prev => {
      const newSet = new Set(prev);
      newSet.delete(album.id);
      return newSet;
    });
  } else {
    setFavoriteAlbums(prev => new Set(prev).add(album.id));
  }
  
  try {
    // 2. Make actual API call
    if (isFavorited) {
      await apiClient.removeFromFavorites(album.id);
    } else {
      await apiClient.addToFavorites(album);
    }
  } catch (error) {
    // 3. Revert optimistic update on failure
    if (isFavorited) {
      setFavoriteAlbums(prev => new Set(prev).add(album.id));
    } else {
      setFavoriteAlbums(prev => {
        const newSet = new Set(prev);
        newSet.delete(album.id);
        return newSet;
      });
    }
    console.error('Error toggling favorite:', error);
  }
};
```

**💡 Concept Explained: Optimistic vs Pessimistic Updates**

**Optimistic Updates** (this app):
- **UX**: Immediate feedback, feels fast
- **Risk**: Might need to rollback on error  
- **Best for**: High-success rate operations (likes, favorites)

**Pessimistic Updates**:
- **UX**: Wait for server confirmation
- **Risk**: Feels slow but always accurate
- **Best for**: Critical operations (payments, deletions)

### **Session Storage for State Persistence**

```typescript
// Store search query when authentication is required
if (searchQuery) {
  sessionStorage.setItem('pendingSearchQuery', searchQuery);
}

// Restore search query after authentication
useEffect(() => {
  if (user) {
    const pendingQuery = sessionStorage.getItem('pendingSearchQuery');
    if (pendingQuery) {
      sessionStorage.removeItem('pendingSearchQuery');
      handleSearch(pendingQuery);
    }
  }
}, [user, handleSearch]);
```

**Use cases for session persistence**:
- **Authentication flows**: Resume after login
- **Form data**: Preserve incomplete forms
- **Navigation state**: Return to same page/tab
- **Search context**: Maintain filters and queries

---

## 🛠️ Practical Exercises

### **Exercise 1: Implement Request Deduplication**

Prevent multiple identical requests from being made simultaneously:

```typescript
class ApiClient {
  private pendingRequests = new Map<string, Promise<any>>();
  
  private async dedupeRequest<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key);
    }
    
    const promise = requestFn().finally(() => {
      this.pendingRequests.delete(key);
    });
    
    this.pendingRequests.set(key, promise);
    return promise;
  }
  
  async searchAlbums(query: string) {
    return this.dedupeRequest(`search:${query}`, () => {
      // Actual API call
    });
  }
}
```

### **Exercise 2: Add Infinite Scroll Loading**

Implement pagination for large result sets:

```typescript
function useInfiniteScroll() {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  
  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    try {
      const newItems = await apiClient.getAlbums(page);
      setItems(prev => [...prev, ...newItems]);
      setPage(prev => prev + 1);
      setHasMore(newItems.length === PAGE_SIZE);
    } catch (error) {
      console.error('Failed to load more items:', error);
    } finally {
      setLoading(false);
    }
  }, [page, loading, hasMore]);
  
  return { items, loadMore, hasMore, loading };
}
```

### **Exercise 3: Implement Request Queuing**

Queue requests when offline, execute when back online:

```typescript
class RequestQueue {
  private queue: QueuedRequest[] = [];
  private isOnline = navigator.onLine;
  
  constructor() {
    window.addEventListener('online', this.processQueue);
    window.addEventListener('offline', () => this.isOnline = false);
  }
  
  async enqueue(request: QueuedRequest) {
    if (this.isOnline) {
      return this.execute(request);
    } else {
      this.queue.push(request);
      return { queued: true };
    }
  }
  
  private processQueue = async () => {
    this.isOnline = true;
    while (this.queue.length > 0) {
      const request = this.queue.shift()!;
      try {
        await this.execute(request);
      } catch (error) {
        // Handle queued request failures
      }
    }
  }
}
```

---

## 🔍 Performance Optimization Patterns

### **Request Batching**

```typescript
// Instead of multiple individual requests
await Promise.all([
  apiClient.getAlbum(id1),
  apiClient.getAlbum(id2), 
  apiClient.getAlbum(id3)
]);

// Batch into single request
await apiClient.getBatchAlbums([id1, id2, id3]);
```

### **Response Streaming**

```typescript
// For large responses, process data as it arrives
async function* streamAlbums(query: string) {
  const response = await fetch(`/api/search?query=${query}&stream=true`);
  const reader = response.body?.getReader();
  
  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = new TextDecoder().decode(value);
    const albums = JSON.parse(chunk);
    yield albums; // Yield each batch as it arrives
  }
}
```

### **Memory Management**

```typescript
useEffect(() => {
  // Cleanup function prevents memory leaks
  return () => {
    // Cancel pending requests
    abortController.abort();
    
    // Clear intervals/timeouts
    clearInterval(intervalId);
    
    // Remove event listeners
    window.removeEventListener('online', handleOnline);
  };
}, []);
```

---

## 🎯 Key Takeaways

1. **Centralized API clients** provide consistency and maintainability
2. **Progressive loading** improves perceived performance
3. **Caching strategies** reduce network requests and improve UX
4. **Error handling** should be graceful and user-friendly
5. **State synchronization** requires careful coordination
6. **Optimistic updates** provide immediate feedback
7. **Request deduplication** prevents unnecessary API calls

---

## 🚀 Next Steps

Ready for Wave 4? You'll explore advanced optimization techniques, deployment strategies, and production-ready patterns that make applications scalable and maintainable.

**Coming up in Wave 4**:
- Performance monitoring and optimization
- Bundle analysis and code splitting
- Production deployment strategies
- Error monitoring and logging
- Accessibility and SEO considerations

---

## 📚 Additional Resources

- **[React Query](https://tanstack.com/query/latest)** - Advanced data fetching library
- **[SWR](https://swr.vercel.app/)** - Data fetching with caching and revalidation
- **[Axios](https://axios-http.com/)** - Feature-rich HTTP client
- **[Web Performance Patterns](https://web.dev/patterns/)** - Google's web performance guide