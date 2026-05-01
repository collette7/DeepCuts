import { useState, useEffect, useCallback, useRef } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { apiClient, SuggestionResponse, SuggestionResult } from '@/lib/api';
import './SearchInput.scss';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent, overrideQuery?: string) => void;
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
  const [closingDropdown, setClosingDropdown] = useState(false);
  const [cache, setCache] = useState(new Map<string, SuggestionResult[]>());
  const [activeIndex, setActiveIndex] = useState(-1);
  const [dropdownLoading, setDropdownLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const closingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const hideDropdown = useCallback(() => {
    if (!showResults) return;
    setClosingDropdown(true);
    closingTimeoutRef.current = setTimeout(() => {
      setShowResults(false);
      setClosingDropdown(false);
    }, 200);
  }, [showResults]);

  const delaySearch = useCallback(async (searchQuery: string) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(async () => {
      if (searchQuery.length < 3) {
        setResults([]);
        setShowResults(false);
        return;
      }

      const cacheKey = searchQuery.toLowerCase();

      // Exact cache hit
      if (cache.has(cacheKey)) {
        const cachedResults = cache.get(cacheKey) || [];
        setResults(cachedResults);
        setShowResults(cachedResults.length > 0);
        return;
      }

      // Prefix cache hit: if a longer query is cached, use it
      for (const [key, value] of cache.entries()) {
        if (cacheKey.startsWith(key) && value.length > 0) {
          setResults(value.slice(0, 5));
          setShowResults(true);
          return;
        }
      }

      setDropdownLoading(true);
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
      } finally {
        setDropdownLoading(false);
      }
    }, 600);
  }, [cache]);

  useEffect(() => {
    delaySearch(value);
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [value, delaySearch]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (resultsRef.current && !resultsRef.current.contains(event.target as Node) &&
          inputRef.current && !inputRef.current.contains(event.target as Node)) {
        hideDropdown();
      }
    };

    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
      if (closingTimeoutRef.current) clearTimeout(closingTimeoutRef.current);
    };
  }, [showResults, hideDropdown]); 

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    setActiveIndex(-1);
    if (newValue.length >= 2) {
      setShowResults(true);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pastedText = e.clipboardData.getData('text').trim();
    if (pastedText.length >= 2) {
      onChange(pastedText);
      setActiveIndex(-1);
      setShowResults(true);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      delaySearch(pastedText);
    }
  };

  const handleInputFocus = () => {
    if (results.length > 0 && value.length >= 2) {
      setShowResults(true);
    }
  };

  const handleResultClick = (result: SuggestionResult) => {
    onChange(result.search_query);
    hideDropdown();
    setActiveIndex(-1);
    const syntheticEvent = { preventDefault: () => {} } as React.FormEvent;
    onSubmit(syntheticEvent, result.search_query);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    hideDropdown();
    setActiveIndex(-1);
    onSubmit(e);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showResults || results.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(prev => (prev < results.length - 1 ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(prev => (prev > 0 ? prev - 1 : results.length - 1));
        break;
      case 'Enter':
        if (activeIndex >= 0 && activeIndex < results.length) {
          e.preventDefault();
          handleResultClick(results[activeIndex]);
        }
        break;
      case 'Escape':
        hideDropdown();
        setActiveIndex(-1);
        break;
    }
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
              onPaste={handlePaste}
              onFocus={handleInputFocus}
              onKeyDown={handleKeyDown}
              className="search-input"
              autoComplete="off"
              role="combobox"
              aria-expanded={showResults && results.length > 0}
              aria-autocomplete="list"
              aria-controls="search-results-listbox"
              aria-activedescendant={activeIndex >= 0 ? `search-result-${results[activeIndex]?.id}` : undefined}
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
      
      {showResults && (
        <div ref={resultsRef} className={`search-results-dropdown${closingDropdown ? ' closing' : ''}`} id="search-results-listbox" role="listbox" aria-label="Search suggestions">
          {dropdownLoading && (
            <div className="search-result-item loading">
              <div className="album-placeholder">♪</div>
              <div className="result-info">
                <div className="result-title">Loading...</div>
              </div>
            </div>
          )}
          {!dropdownLoading && results.length === 0 && (
            <div className="search-result-item no-results">
              <div className="album-placeholder">♪</div>
              <div className="result-info">
                <div className="result-title">No results found</div>
              </div>
            </div>
          )}
          {results.map((result, idx) => (
            <div 
              key={result.id}
              id={`search-result-${result.id}`}
              className={`search-result-item ${idx === activeIndex ? 'active' : ''}`}
              onClick={() => handleResultClick(result)}
              role="option"
              aria-selected={idx === activeIndex}
            >
              <div className="result-album-cover">
                {result.thumb ? (
                  <img 
                    src={result.thumb} 
                    alt={result.title} 
                    className="album-thumbnail"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNSAzNUMzMC41MjI4IDM1IDM1IDMwLjUyMjggMzUgMjVDMzUgMTkuNDc3MiAzMC41MjI4IDE1IDI1IDE1QzE5LjQ3NzIgMTUgMTUgMTkuNDc3MiAxNSAyNUMxNSAzMC41MjI4IDE5LjQ3NzIgMzUgMjUgMzZaIiBzdHJva2U9IiM5Q0EzQUYiIHN0cm9rZS13aWR0aD0iMiIvPgo8L3N2Zz4K';
                    }}
                  />
                ) : (
                  <div className="album-placeholder">♪</div>
                )}
              </div>
              <div className="result-info">
                <div className="result-title">{result.title}</div>
                <div className="result-metadata">
                  {result.artist && <span className="result-artist">{result.artist}</span>}
                  {result.artist && result.year && <span className="result-meta-separator"> · </span>}
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