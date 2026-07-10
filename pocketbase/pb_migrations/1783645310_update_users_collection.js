/// <reference path="../pb_data/types.d.ts" />

// Extends PocketBase's built-in "users" auth collection with the profile
// fields DeepCuts needs, merging what used to be split across Supabase's
// auth.users and public.users tables into a single auth record.
migrate((app) => {
  const collection = app.findCollectionByNameOrId("users")

  collection.fields.add(new Field({
    type: "text",
    name: "username",
    required: false,
    max: 100,
  }))

  collection.fields.add(new Field({
    type: "json",
    name: "preferences",
    required: false,
    maxSize: 2000000,
  }))

  collection.fields.add(new Field({
    type: "text",
    name: "spotify_user_id",
    required: false,
    max: 200,
  }))

  collection.fields.add(new Field({
    type: "text",
    name: "spotify_access_token",
    required: false,
    max: 2000,
    hidden: true,
  }))

  // Self-service signup/login only; listing and self-deletion stay
  // superuser-only (FastAPI's admin-authenticated client).
  collection.listRule = null
  collection.viewRule = "id = @request.auth.id"
  collection.createRule = ""
  collection.updateRule = "id = @request.auth.id"
  collection.deleteRule = null

  app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("users")

  for (const name of ["username", "preferences", "spotify_user_id", "spotify_access_token"]) {
    const field = collection.fields.getByName(name)
    if (field) {
      collection.fields.removeById(field.id)
    }
  }

  collection.listRule = null
  collection.viewRule = null
  collection.createRule = null
  collection.updateRule = null
  collection.deleteRule = null

  app.save(collection)
})
