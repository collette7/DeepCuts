import PocketBase, { type RecordModel } from 'pocketbase'

const pocketbaseUrl = process.env.NEXT_PUBLIC_POCKETBASE_URL

if (!pocketbaseUrl) {
  throw new Error('Missing PocketBase environment variable: NEXT_PUBLIC_POCKETBASE_URL')
}

export const pb = new PocketBase(pocketbaseUrl)

export type AuthenticatedUser = RecordModel
