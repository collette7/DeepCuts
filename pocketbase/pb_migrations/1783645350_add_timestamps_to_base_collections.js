/// <reference path="../pb_data/types.d.ts" />

// Fixes a gap from the earlier collection migrations: base collections
// don't get `created`/`updated` autodate fields automatically the way
// auth collections do — they must be declared explicitly. Discovered via
// live smoke testing when `sort=-created` on favorites returned a 400,
// since the field didn't exist. All six base collections need it: the
// service layer (favorites.py, search_sessions.py) reads `created` on
// every record it returns.
migrate((app) => {
  const collectionNames = [
    "albums",
    "favorites",
    "search_inputs",
    "search_outputs",
    "search_clicks",
    "filtered_albums",
  ]

  for (const name of collectionNames) {
    const collection = app.findCollectionByNameOrId(name)
    collection.fields.add(new Field({
      type: "autodate",
      name: "created",
      onCreate: true,
      onUpdate: false,
    }))
    collection.fields.add(new Field({
      type: "autodate",
      name: "updated",
      onCreate: true,
      onUpdate: true,
    }))
    app.save(collection)
  }
}, (app) => {
  const collectionNames = [
    "albums",
    "favorites",
    "search_inputs",
    "search_outputs",
    "search_clicks",
    "filtered_albums",
  ]

  for (const name of collectionNames) {
    const collection = app.findCollectionByNameOrId(name)
    for (const fieldName of ["created", "updated"]) {
      const field = collection.fields.getByName(fieldName)
      if (field) {
        collection.fields.removeById(field.id)
      }
    }
    app.save(collection)
  }
})
