/// <reference path="../pb_data/types.d.ts" />

// Recreates public.search_input, search_output, search_session_clicks, and
// search_session_filtered_albums, plus the favorites.search_session
// relation that was deferred from the favorites migration (search_inputs
// didn't exist yet at that point).
//
// Ownership rules use @request.auth.email against a plain user_email text
// field rather than a relation, mirroring the original Supabase policies
// (auth.jwt()->>'email' = user_email) — these tables allow anonymous
// writes (no logged-in user), so a required user relation isn't a fit.
migrate((app) => {
  const searchInputs = new Collection({
    type: "base",
    name: "search_inputs",
    listRule: "@request.auth.id != '' && user_email = @request.auth.email",
    viewRule: "@request.auth.id != '' && user_email = @request.auth.email",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    fields: [
      { type: "text", name: "query", required: true, max: 2000 },
      { type: "text", name: "user_email", required: false, max: 300 },
      { type: "text", name: "ip_address", required: false, max: 100 },
      { type: "text", name: "user_agent", required: false, max: 1000 },
      { type: "text", name: "ai_model", required: false, max: 200 },
      { type: "number", name: "results_count", required: false },
      { type: "number", name: "filtered_count", required: false },
      { type: "number", name: "raw_results_count", required: false },
      { type: "editor", name: "raw_response", required: false },
    ],
  })
  app.save(searchInputs)

  const searchOutputs = new Collection({
    type: "base",
    name: "search_outputs",
    listRule: "",
    viewRule: "",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    fields: [
      {
        type: "relation",
        name: "session",
        required: true,
        collectionId: searchInputs.id,
        cascadeDelete: true,
        maxSelect: 1,
      },
      { type: "text", name: "album_title", required: true, max: 500 },
      { type: "text", name: "album_artist", required: true, max: 500 },
      { type: "number", name: "album_year", required: false },
      { type: "text", name: "album_genre", required: false, max: 200 },
      { type: "number", name: "rank", required: false },
      { type: "bool", name: "is_verified", required: false },
      { type: "text", name: "verification_source", required: false, max: 200 },
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_search_outputs_session_album_rank ON search_outputs (session, album_title, album_artist, rank)",
    ],
  })
  app.save(searchOutputs)

  const searchClicks = new Collection({
    type: "base",
    name: "search_clicks",
    listRule: "@request.auth.id != '' && user_email = @request.auth.email",
    viewRule: "@request.auth.id != '' && user_email = @request.auth.email",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    fields: [
      {
        type: "relation",
        name: "session",
        required: false,
        collectionId: searchInputs.id,
        cascadeDelete: true,
        maxSelect: 1,
      },
      { type: "text", name: "album_title", required: true, max: 500 },
      { type: "text", name: "album_artist", required: true, max: 500 },
      {
        type: "select",
        name: "action",
        required: true,
        maxSelect: 1,
        values: ["click", "favorite", "unfavorite"],
      },
      { type: "text", name: "user_email", required: false, max: 300 },
    ],
  })
  app.save(searchClicks)

  const filteredAlbums = new Collection({
    type: "base",
    name: "filtered_albums",
    listRule: "@request.auth.id != '' && session.user_email = @request.auth.email",
    viewRule: "@request.auth.id != '' && session.user_email = @request.auth.email",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    fields: [
      {
        type: "relation",
        name: "session",
        required: true,
        collectionId: searchInputs.id,
        cascadeDelete: true,
        maxSelect: 1,
      },
      { type: "text", name: "album_title", required: true, max: 500 },
      { type: "text", name: "album_artist", required: true, max: 500 },
      { type: "text", name: "filter_reason", required: false, max: 500 },
    ],
  })
  app.save(filteredAlbums)

  // Deferred from the favorites migration: search_inputs now exists.
  const favorites = app.findCollectionByNameOrId("favorites")
  favorites.fields.add(new Field({
    type: "relation",
    name: "search_session",
    required: false,
    collectionId: searchInputs.id,
    cascadeDelete: false,
    maxSelect: 1,
  }))
  app.save(favorites)
}, (app) => {
  const favorites = app.findCollectionByNameOrId("favorites")
  const searchSessionField = favorites.fields.getByName("search_session")
  if (searchSessionField) {
    favorites.fields.removeById(searchSessionField.id)
    app.save(favorites)
  }

  for (const name of ["filtered_albums", "search_clicks", "search_outputs", "search_inputs"]) {
    const collection = app.findCollectionByNameOrId(name)
    if (collection) {
      app.delete(collection)
    }
  }
})
