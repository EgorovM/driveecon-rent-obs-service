import smtplib
import socket
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


class _SMTP_IPV4(smtplib.SMTP):
    """Обычный SMTP (порт 587): только IPv4 — обходит зависания на битом IPv6."""

    def _get_socket(self, host, port, timeout):
        if timeout is not None and not timeout:
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        last: OSError | None = None
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            try:
                sock = socket.socket(res[0], res[1], res[2])
                sock.settimeout(timeout)
                sock.connect(res[4])
                return sock
            except OSError as e:
                last = e
                continue
        if last:
            raise last
        raise OSError(f"SMTP IPv4: не удалось подключиться к {host}:{port}")


class _SMTP_SSL_IPV4(smtplib.SMTP_SSL):
    """SMTP_SSL (порт 465): только IPv4."""

    def _get_socket(self, host, port, timeout):
        if timeout is not None and not timeout:
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        last: OSError | None = None
        for res in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            try:
                sock = socket.socket(res[0], res[1], res[2])
                sock.settimeout(timeout)
                sock.connect(res[4])
                return self.context.wrap_socket(sock, server_hostname=self._host)
            except OSError as e:
                last = e
                continue
        if last:
            raise last
        raise OSError(f"SMTP_SSL IPv4: не удалось подключиться к {host}:{port}")


def _open_smtp():
    """Открывает соединение с учётом настроек (SSL / STARTTLS / IPv4)."""
    host = settings.smtp_host
    port = settings.smtp_port
    timeout = settings.smtp_timeout
    ctx = _ssl_context()
    force_v4 = settings.smtp_force_ipv4

    if settings.smtp_use_ssl:
        if force_v4:
            smtp = _SMTP_SSL_IPV4(host, port, timeout=timeout, context=ctx)
        else:
            smtp = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx)
    else:
        if force_v4:
            smtp = _SMTP_IPV4(host, port, timeout=timeout)
        else:
            smtp = smtplib.SMTP(host, port, timeout=timeout)
        smtp.starttls(context=ctx)

    if settings.smtp_debug:
        smtp.set_debuglevel(1)

    return smtp


def _send(to_addr: str, subject: str, body_text: str) -> None:
    if not settings.smtp_user or not settings.smtp_pass:
        raise RuntimeError("SMTP_USER и SMTP_PASS не заданы в окружении")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to_addr
    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    smtp = _open_smtp()
    try:
        smtp.login(settings.smtp_user, settings.smtp_pass)
        smtp.sendmail(settings.smtp_user, [to_addr], msg.as_string())
    finally:
        try:
            smtp.quit()
        except Exception:
            smtp.close()


def send_tenant_payment_reminder(
    *,
    tenant_email: str,
    property_name: str,
    address: str,
    rent_end_iso: str,
    confirm_url: str,
) -> None:
    subject = f"Напоминание об оплате аренды: {property_name}"
    body = (
        f"Здравствуйте!\n\n"
        f"Через 3 дня заканчивается срок аренды по объекту «{property_name}».\n"
        f"Адрес: {address}\n"
        f"Дата окончания аренды: {rent_end_iso}\n\n"
        f"Пожалуйста, подтвердите оплату по ссылке (это эквивалент ответа на письмо):\n"
        f"{confirm_url}\n\n"
        f"После подтверждения владелец получит уведомление.\n"
    )
    _send(tenant_email, subject, body)


def send_owner_paid(*, owner_email: str, property_name: str, address: str, tenant_name: str) -> None:
    subject = f"Оплата подтверждена: {property_name}"
    body = (
        f"Арендатор {tenant_name} подтвердил оплату по объекту.\n\n"
        f"Объект: {property_name}\n"
        f"Адрес: {address}\n"
    )
    _send(owner_email, subject, body)


def send_owner_not_paid(*, owner_email: str, property_name: str, address: str, tenant_name: str, rent_end_iso: str) -> None:
    subject = f"Нет подтверждения оплаты: {property_name}"
    body = (
        f"По объекту «{property_name}» не получено подтверждение оплаты от арендатора {tenant_name}.\n\n"
        f"Адрес: {address}\n"
        f"Дата окончания аренды: {rent_end_iso}\n"
    )
    _send(owner_email, subject, body)


def send_demo(to_email: str, subject: str, body: str) -> None:
    _send(to_email, subject, body)
