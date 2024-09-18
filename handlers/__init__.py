from .main_menu import register_main_menu_handlers
from .support import register_support_handlers
from .faq import register_faq_handlers
from .subscription import register_subscription_handlers
from .alerts import register_alert_handlers
from .requests import register_request_handlers
from .payment_handler import app
from .admin_commands import register_admin_handlers
from .new_sub import register_sub2_handlers


def register_all_handlers(dp):
    register_main_menu_handlers(dp)
    register_support_handlers(dp)
    register_faq_handlers(dp)
    #register_subscription_handlers(dp)
    register_alert_handlers(dp)
    register_request_handlers(dp)
    register_admin_handlers(dp)
    register_sub2_handlers(dp)




