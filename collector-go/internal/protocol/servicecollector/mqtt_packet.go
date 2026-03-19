package servicecollector

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
)

func encodeRemainingLength(n int) []byte {
	out := make([]byte, 0, 4)
	for {
		digit := byte(n % 128)
		n /= 128
		if n > 0 {
			digit |= 0x80
		}
		out = append(out, digit)
		if n == 0 {
			break
		}
	}
	return out
}

func writeString(buf *bytes.Buffer, s string) {
	_ = binary.Write(buf, binary.BigEndian, uint16(len(s)))
	_, _ = buf.WriteString(s)
}

func mqttConnectPacket(clientID, username, password string, keepaliveSec int) []byte {
	vh := bytes.NewBuffer(nil)
	writeString(vh, "MQTT")
	_ = vh.WriteByte(0x04) // MQTT 3.1.1
	flags := byte(0x02)    // clean session
	if username != "" {
		flags |= 0x80
	}
	if password != "" {
		flags |= 0x40
	}
	_ = vh.WriteByte(flags)
	_ = binary.Write(vh, binary.BigEndian, uint16(keepaliveSec))

	pl := bytes.NewBuffer(nil)
	writeString(pl, clientID)
	if username != "" {
		writeString(pl, username)
	}
	if password != "" {
		writeString(pl, password)
	}

	remaining := vh.Len() + pl.Len()
	pkt := bytes.NewBuffer(nil)
	_ = pkt.WriteByte(0x10)
	_, _ = pkt.Write(encodeRemainingLength(remaining))
	_, _ = pkt.Write(vh.Bytes())
	_, _ = pkt.Write(pl.Bytes())
	return pkt.Bytes()
}

func mqttSubscribePacket(packetID uint16, topic string) []byte {
	payload := bytes.NewBuffer(nil)
	writeString(payload, topic)
	_ = payload.WriteByte(0x00)
	vh := bytes.NewBuffer(nil)
	_ = binary.Write(vh, binary.BigEndian, packetID)

	pkt := bytes.NewBuffer(nil)
	_ = pkt.WriteByte(0x82)
	_, _ = pkt.Write(encodeRemainingLength(vh.Len() + payload.Len()))
	_, _ = pkt.Write(vh.Bytes())
	_, _ = pkt.Write(payload.Bytes())
	return pkt.Bytes()
}

func mqttPublishPacket(topic, message string) []byte {
	payload := bytes.NewBuffer(nil)
	writeString(payload, topic)
	_, _ = payload.WriteString(message)
	pkt := bytes.NewBuffer(nil)
	_ = pkt.WriteByte(0x30)
	_, _ = pkt.Write(encodeRemainingLength(payload.Len()))
	_, _ = pkt.Write(payload.Bytes())
	return pkt.Bytes()
}

func mqttUnsubscribePacket(packetID uint16, topic string) []byte {
	payload := bytes.NewBuffer(nil)
	writeString(payload, topic)
	vh := bytes.NewBuffer(nil)
	_ = binary.Write(vh, binary.BigEndian, packetID)

	pkt := bytes.NewBuffer(nil)
	_ = pkt.WriteByte(0xA2)
	_, _ = pkt.Write(encodeRemainingLength(vh.Len() + payload.Len()))
	_, _ = pkt.Write(vh.Bytes())
	_, _ = pkt.Write(payload.Bytes())
	return pkt.Bytes()
}

func readMQTTPacket(r io.Reader) (byte, []byte, error) {
	head := make([]byte, 1)
	if _, err := io.ReadFull(r, head); err != nil {
		return 0, nil, err
	}
	remaining, err := readRemainingLength(r)
	if err != nil {
		return 0, nil, err
	}
	body := make([]byte, remaining)
	if _, err := io.ReadFull(r, body); err != nil {
		return 0, nil, err
	}
	return head[0], body, nil
}

func readRemainingLength(r io.Reader) (int, error) {
	multiplier := 1
	value := 0
	for i := 0; i < 4; i++ {
		b := make([]byte, 1)
		if _, err := io.ReadFull(r, b); err != nil {
			return 0, err
		}
		value += int(b[0]&127) * multiplier
		if (b[0] & 128) == 0 {
			return value, nil
		}
		multiplier *= 128
	}
	return 0, fmt.Errorf("malformed remaining length")
}
