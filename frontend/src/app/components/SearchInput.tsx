import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { apiClient, SuggestionResponse, SuggestionResult } from '@/lib/api';
import './SearchInput.scss';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading?: boolean;
  placeholder?: string;
  variant?: 'default' | 'hero';
  showButton?: boolean;
  className?: string;
}

export default function SearchInput({
  value,
  onChange,
  onSubmit,
  loading = false,
  placeholder = "Search for albums",
  variant = 'default',
  showButton = true,
  className = ''
}: SearchInputProps) {
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
          // Deduplicate by normalizing titles
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
    delaySearch(value);
  }, [value, delaySearch]);

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
    const newValue = e.target.value;
    onChange(newValue);
    if (newValue.length >= 2) {
      setShowResults(true);
    }
  };

  const handleInputFocus = () => {
    if (results.length > 0 && value.length >= 2) {
      setShowResults(true);
    }
  };

  const handleResultClick = (result: SuggestionResult) => {
    onChange(result.title);
    setShowResults(false);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setShowResults(false);
    onSubmit(e);
  };

  return (
    <div className={`search-input-container ${variant} ${className}`}>
      <form onSubmit={handleFormSubmit} className="search-input-form">
        <div className="search-field">
          <div className="search-input-wrapper">
            <Search className="search-icon" size={variant === 'hero' ? 24 : 20} />
            <input
              ref={inputRef}
              type="text"
              placeholder={placeholder}
              value={value}
              onChange={handleInputChange}
              onFocus={handleInputFocus}
              className="search-input"
              autoComplete="off"
              required
            />
          </div>
          {showButton && (
            <button
              type="submit"
              disabled={loading}
              className="search-submit-btn"
              aria-label="Search"
            >
              <div className="search-btn-icon">
                {loading ? (
                  <div className="loading-spinner" />
                ) : variant === 'hero' ? (
                  <ArrowRight size={20} color="white" />
                ) : (
                  'Search'
                )}
              </div>
            </button>
          )}
        </div>
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
                  {result.year && <time dateTime={result.year.toString()}>{result.year}</time>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}