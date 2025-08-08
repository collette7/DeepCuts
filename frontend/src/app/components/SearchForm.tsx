import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, SuggestionResponse, SuggestionResult } from '@/lib/api';
import './SearchForm.scss';

interface SearchFormProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
}

export default function SearchForm({ 
  searchQuery, 
  onSearchQueryChange, 
  onSubmit, 
  loading 
}: SearchFormProps) {
  const [results, setResults] = useState<SuggestionResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [cache, setCache] = useState(new Map<string, SuggestionResult[]>());
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const delaySearch = useCallback(async (searchQuery: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(async () => {
      if (searchQuery.length < 2) {
        setResults([]);
        setShowResults(false);
        return;
      }

      
      const cacheKey = searchQuery.toLowerCase();
      if (cache.has(cacheKey)) {
        const cachedResults = cache.get(cacheKey) || [];
        setResults(cachedResults);
        setShowResults(cachedResults.length > 0);
        return;
      }

      try {
        const data: SuggestionResponse = await apiClient.searchDiscogs(searchQuery);
        
        if (data.results && data.results.length > 0) {
          // Deduplicate by normalizing titles (remove extra info, case insensitive)
          const deduplicatedResults = data.results.reduce((acc: SuggestionResult[], current) => {
            const normalizeTitle = (title: string) => {
              return title
                .toLowerCase()
                .replace(/\s*-\s*.*$/, '')
                .replace(/[^\w\s]/g, '')
                .trim();
            };
            
            const currentNormalized = normalizeTitle(current.title);
            const isDuplicate = acc.some(existing => 
              normalizeTitle(existing.title) === currentNormalized
            );
            
            if (!isDuplicate) {
              acc.push(current);
            }
            
            return acc;
          }, []);
          
          const limitedResults = deduplicatedResults.slice(0, 5); 
          setCache(prev => new Map(prev.set(cacheKey, limitedResults)));
          setResults(limitedResults);
          setShowResults(true);
        } else {
          setResults([]);
          setShowResults(false);
        }
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
        setShowResults(false);
      }
    }, 300);
  }, [cache]);

  useEffect(() => {
    delaySearch(searchQuery);
  }, [searchQuery, delaySearch]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (resultsRef.current && !resultsRef.current.contains(event.target as Node) &&
          inputRef.current && !inputRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showResults]); 

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    onSearchQueryChange(value);
    if (value.length >= 2) {
      setShowResults(true);
    }
  };

  const handleInputFocus = () => {
    if (results.length > 0 && searchQuery.length >= 2) {
      setShowResults(true);
    }
  };

  const handleResultClick = (result: SuggestionResult) => {
    onSearchQueryChange(result.title);
    setShowResults(false);
    
  };
  return (
    <div className="search-section">
      <div className="search-form-wrapper">
        <form onSubmit={onSubmit} className="search-form">
          <div className="search-input-container">
            <svg className="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search for albums"
              value={searchQuery}
              onChange={handleInputChange}
              onFocus={handleInputFocus}
              className="search-input"
              autoComplete="off"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="search-button"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {showResults && results.length > 0 && (
          <div ref={resultsRef} className="search-results-dropdown">
          {results.map((result) => (
            <div 
              key={result.id} 
              className="search-result-item"
              onClick={() => handleResultClick(result)}
            >
              <div className="result-album-cover">
                {result.thumb ? (
                  <img 
                    src={result.thumb} 
                    alt={result.title} 
                    className="album-thumbnail"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNSAzNUMzMC41MjI4IDM1IDM1IDMwLjUyMjggMzUgMjVDMzUgMTkuNDc3MiAzMC41MjI4IDE1IDI1IDE1QzE5LjQ3NzIgMTUgMTUgMTkuNDc3MiAxNSAyNUMxNSAzMC41MjI4IDE5LjQ3NzIgMzUgMjUgMzVaIiBzdHJva2U9IiM5Q0EzQUYiIHN0cm9rZS13aWR0aD0iMiIvPgo8L3N2Zz4K';
                    }}
                  />
                ) : (
                  <div className="album-placeholder">♪</div>
                )}
              </div>
              <div className="result-info">
                <div className="result-title">{result.title}</div>
                <div className="result-metadata">
                  {result.year && <span>{result.year}</span>}
                </div>
              </div>
            </div>
          ))}
          </div>
        )}
      </div>
    </div>
  );
}