import SearchInput from './SearchInput';
import './HeroHeader.scss';

interface HeroHeaderProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
}

export default function HeroHeader({ 
  searchQuery, 
  onSearchQueryChange, 
  onSubmit, 
  loading 
}: HeroHeaderProps) {

  return (
    <header className="hero-header">
      <div className="hero-content">
        <div className="hero-text">
          <h1 className="hero-title">
            <span>One album in.</span>
            <span>Endless obsessions out.</span>
          </h1>
          <p className="hero-description">
            Finally: music discovery that doesn&apos;t insult your intelligence. Just enter an 
            album you love—we&apos;ll recommend others that hit the same.
          </p>
        </div>
        
        <div className="hero-search">
          <SearchInput
            value={searchQuery}
            onChange={onSearchQueryChange}
            onSubmit={onSubmit}
            loading={loading}
            placeholder="Type an album to get similar recs"
            variant="hero"
            showButton={true}
          />
        </div>
      </div>
    </header>
  );
}