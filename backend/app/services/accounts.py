from app.clients.pocketbase import escape_filter_value, get_shared_pocketbase_client
from app.models.accounts import AccountDeletionResponse
from app.services.auth import AuthenticatedUser


class AccountService:
    def __init__(self) -> None:
        self.client = get_shared_pocketbase_client()

    async def delete_user_data(self, user: AuthenticatedUser) -> AccountDeletionResponse:
        sessions = await self.client.list_all_records(
            "search_inputs",
            filter=f"user_email = {escape_filter_value(user.email)}",
        )
        for session in sessions:
            await self.client.delete_record("search_inputs", session["id"])

        await self.client.delete_record("users", user.id)
        return AccountDeletionResponse(
            success=True,
            deleted_search_sessions=len(sessions),
        )


account_service = AccountService()
