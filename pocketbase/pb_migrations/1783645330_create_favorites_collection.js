/// <reference path="../pb_data/types.d.ts" />

// Recreates public.favorites. Uses relation fields for user/album/
// source_album (Supabase FKs), with cascadeDelete mirroring the original
// ON DELETE CASCADE (user, album) vs ON DELETE SET NULL (source_album)
// behavior. The search_session relation is added later, in the search
// collections migration, since search_inputs doesn't exist yet here.
migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users")
  const albumsCollection = app.findCollectionByNameOrId("albums")

  const collection = new Collection({
    type: "base",
    name: "favorites",
    listRule: "user = @request.auth.id",
    viewRule: "user = @request.auth.id",
    createRule: "user = @request.auth.id",
    updateRule: "user = @request.auth.id",
    deleteRule: "user = @request.auth.id",
    fields: [
      {
        type: "relation",
        name: "user",
        required: true,
        collectionId: usersCollection.id,
        cascadeDelete: true,
        maxSelect: 1,
      },
      {
        type: "relation",
        name: "album",
        required: true,
        collectionId: albumsCollection.id,
        cascadeDelete: true,
        maxSelect: 1,
      },
      {
        type: "relation",
        name: "source_album",
        required: false,
        collectionId: albumsCollection.id,
        cascadeDelete: false,
        maxSelect: 1,
      },
      { type: "text", name: "reasoning", required: false, max: 2000 },
    ],
    indexes: [
      "CREATE UNIQUE INDEX idx_favorites_user_album ON favorites (user, album)",
    ],
  })

  app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("favorites")
  app.delete(collection)
})
