/// <reference path="../pb_data/types.d.ts" />

// Fixes a schema mismatch from the original search_clicks migration:
// Postgres's NOT NULL allows empty string, but PocketBase's `required`
// flag on a text field rejects both null AND empty string. The original
// app inserted click events with blank album_title/album_artist for
// some interactions (e.g. clicks not tied to a specific album row), so
// requiring non-blank values here rejected real historical data during
// recovery from the Supabase backup.
migrate((app) => {
  const collection = app.findCollectionByNameOrId("search_clicks")

  for (const name of ["album_title", "album_artist"]) {
    const field = collection.fields.getByName(name)
    field.required = false
  }

  app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("search_clicks")

  for (const name of ["album_title", "album_artist"]) {
    const field = collection.fields.getByName(name)
    field.required = true
  }

  app.save(collection)
})
