import { MagnifyingGlassIcon } from '@radix-ui/react-icons';

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
  return (
    <div className="search-section">
      <form onSubmit={onSubmit} className="search-form">
        <div className="search-input-container">
          <MagnifyingGlassIcon className="search-icon" />
          <input
            type="text"
            placeholder="Search for albums"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            className="search-input"
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
    </div>
  );
}