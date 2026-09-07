/// <reference path="../pb_data/types.d.ts" />

migrate((app) => {
  const settings = app.settings()
  settings.rateLimits.enabled = true
  settings.trustedProxy.headers = ["X-Forwarded-For"]
  app.save(settings)

  const users = app.findCollectionByNameOrId("users")
  users.authRule = "verified = true"
  app.save(users)

  const searchOutputs = app.findCollectionByNameOrId("search_outputs")
  const ownerRule = "@request.auth.id != '' && session.user_email = @request.auth.email"
  searchOutputs.listRule = ownerRule
  searchOutputs.viewRule = ownerRule
  app.save(searchOutputs)

  const searchInputs = app.findCollectionByNameOrId("search_inputs")
  for (const name of ["ip_address", "user_agent", "raw_response"]) {
    const field = searchInputs.fields.getByName(name)
    if (field) {
      searchInputs.fields.removeById(field.id)
    }
  }
  app.save(searchInputs)
}, (app) => {
  const settings = app.settings()
  settings.rateLimits.enabled = false
  settings.trustedProxy.headers = []
  app.save(settings)

  const users = app.findCollectionByNameOrId("users")
  users.authRule = ""
  app.save(users)

  const searchOutputs = app.findCollectionByNameOrId("search_outputs")
  searchOutputs.listRule = ""
  searchOutputs.viewRule = ""
  app.save(searchOutputs)

  const searchInputs = app.findCollectionByNameOrId("search_inputs")
  searchInputs.fields.add(new Field({ type: "text", name: "ip_address", required: false, max: 100 }))
  searchInputs.fields.add(new Field({ type: "text", name: "user_agent", required: false, max: 1000 }))
  searchInputs.fields.add(new Field({ type: "editor", name: "raw_response", required: false }))
  app.save(searchInputs)
})
