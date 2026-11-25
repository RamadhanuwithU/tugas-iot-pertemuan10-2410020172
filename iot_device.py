"""
Simulasi perangkat IoT (pengganti ESP32) - NIM 2410020172.
1. Membaca suhu DHT22 (simulasi) dan mempublikasikan ke MQTT setiap 3 detik
2. Subscribe ke topik kontrol relay ("ON"/"OFF") untuk mengendalikan GPIO 26
3. Subscribe ke topik kontrol PWM (0-255) untuk kecerahan LED pada GPIO 2
"""
import time
import random
import threading
import paho.mqtt.client as mqtt

# ================= KONFIGURASI =================
NIM = "2410020172"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = f"PythonDevice-{NIM}"

TOPIC_SUHU = f"iot/{NIM}/sensor/suhu"
TOPIC_RELAY = f"iot/{NIM}/aktuator/relay"
TOPIC_PWM = f"iot/{NIM}/aktuator/pwm"
TOPIC_STATUS_RELAY = f"iot/{NIM}/status/relay"
TOPIC_STATUS_PWM = f"iot/{NIM}/status/pwm"

GPIO_RELAY = 26
GPIO_LED_PWM = 2
INTERVAL_PUBLISH = 3  # detik

# ================= STATE GLOBAL =================
relay_state = "OFF"
pwm_value = 0


# ================= AKTUATOR (SIMULASI GPIO) =================
def set_relay_gpio(state: str):
    """Simulasi pengendalian Relay pada GPIO 26."""
    level = "HIGH" if state == "ON" else "LOW"
    status_text = "MENYALA" if state == "ON" else "MATI"
    print(f"[AKTUATOR][GPIO {GPIO_RELAY}] Relay {status_text} ({level})")


def set_led_pwm_gpio(value: int):
    """Simulasi pengaturan kecerahan LED PWM (0-255) pada GPIO 2."""
    persen = round((value / 255) * 100, 1)
    print(f"[AKTUATOR][GPIO {GPIO_LED_PWM}] Kecerahan LED PWM = {value}/255 ({persen}%)")
    return persen


# ================= CALLBACK MQTT =================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MQTT] Terhubung ke broker")
        client.subscribe(TOPIC_RELAY, qos=0)
        client.subscribe(TOPIC_PWM, qos=0)
        print(f"[MQTT] Subscribe ke topik: {TOPIC_RELAY}")
        print(f"[MQTT] Subscribe ke topik: {TOPIC_PWM}")
    else:
        print(f"[MQTT] Gagal terhubung, kode: {reason_code}")


def on_message(client, userdata, msg):
    global relay_state, pwm_value
    payload = msg.payload.decode("utf-8").strip()
    print(f"[MQTT] Pesan masuk [{msg.topic}]: {payload}")

    if msg.topic == TOPIC_RELAY:
        cmd = payload.upper()
        if cmd in ("ON", "1"):
            relay_state = "ON"
        elif cmd in ("OFF", "0"):
            relay_state = "OFF"
        else:
            print(f"[AKTUATOR][GPIO {GPIO_RELAY}] Perintah relay tidak dikenal: {payload}")
            return

        set_relay_gpio(relay_state)
        client.publish(TOPIC_STATUS_RELAY, relay_state, qos=0)
        print(f"[MQTT] Publish status: {TOPIC_STATUS_RELAY} -> {relay_state}")

    elif msg.topic == TOPIC_PWM:
        try:
            nilai = int(float(payload))
        except ValueError:
            print(f"[AKTUATOR][GPIO {GPIO_LED_PWM}] Nilai PWM tidak valid: {payload}")
            return

        if not (0 <= nilai <= 255):
            print(f"[AKTUATOR][GPIO {GPIO_LED_PWM}] Nilai PWM di luar rentang (0-255): {nilai}")
            return

        pwm_value = nilai
        persen = set_led_pwm_gpio(pwm_value)
        status_pwm = f"{pwm_value} / 255 ({persen}%)"
        client.publish(TOPIC_STATUS_PWM, status_pwm, qos=0)
        print(f"[MQTT] Publish status: {TOPIC_STATUS_PWM} -> {status_pwm}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MQTT] Terputus (kode: {reason_code}). Mencoba reconnect...")


# ================= PEMBACAAN SENSOR =================
def baca_suhu():
    """
    Simulasi pembacaan suhu sensor DHT22 (24.0 - 30.0 °C).
    Jika menggunakan DHT22 fisik di Raspberry Pi, ganti dengan Adafruit_DHT.
    """
    base = 27.0
    noise = random.uniform(-1.5, 1.5)
    return round(base + noise, 2)


# ================= THREAD PUBLISH SENSOR =================
def publish_loop(client):
    while True:
        try:
            suhu = baca_suhu()
            if suhu is not None:
                client.publish(TOPIC_SUHU, str(suhu), qos=0)
                print(f"[SENSOR DHT22] Publish suhu: {TOPIC_SUHU} -> {suhu} °C")
        except Exception as e:
            print(f"[SENSOR] Error publish: {e}")
        time.sleep(INTERVAL_PUBLISH)


# ================= MAIN =================
def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    print(f"[MQTT] Menghubungkan ke {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    time.sleep(1)

    publisher = threading.Thread(target=publish_loop, args=(client,), daemon=True)
    publisher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Menghentikan program...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
