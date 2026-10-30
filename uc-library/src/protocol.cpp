#include "presonus/uc/protocol.hpp"
#include <algorithm>
#include <cstring>
#include <limits>

namespace presonus::uc {
namespace {
std::uint16_t le16(const std::uint8_t *p) {
  return p[0] | (std::uint16_t(p[1]) << 8);
}
void put16(Bytes &out, std::uint16_t n) {
  out.push_back(n & 255);
  out.push_back(n >> 8);
}
void header(const Bytes &b) {
  if (b.size() < 6 || b[0] != 'U' || b[1] != 'C' || b[2] != 0 || b[3] != 1)
    throw ProtocolError("invalid UC transport header or unsupported version");
}
Bytes wrap(const Event &event, std::uint16_t field) {
  auto body = encode_event(event);
  Bytes out = {'U', 'C', 0, 1};
  put16(out, field);
  out.insert(out.end(), body.begin(), body.end());
  return out;
}
} // namespace
Bytes encode_event(const Event &e) {
  if (e.payload.size() > max_event_size - 6)
    throw ProtocolError("UC event exceeds 16384 bytes");
  Bytes out = {std::uint8_t(e.type >> 8), std::uint8_t(e.type & 255)};
  put16(out, e.route_a);
  put16(out, e.route_b);
  out.insert(out.end(), e.payload.begin(), e.payload.end());
  return out;
}
Event decode_event(const Bytes &b) {
  if (b.size() < 6 || b.size() > max_event_size)
    throw ProtocolError("invalid UC event size");
  return {std::uint16_t((std::uint16_t(b[0]) << 8) | b[1]), le16(b.data() + 2),
          le16(b.data() + 4), Bytes(b.begin() + 6, b.end())};
}
Bytes encode_tcp(const Event &e) {
  return wrap(e, std::uint16_t(e.payload.size() <= max_event_size - 6
                                   ? e.payload.size() + 6
                                   : 0));
}
Bytes encode_udp(const Datagram &d) {
  // MulticastConnection writes header and event into one 0x4000-byte buffer.
  if (d.event.payload.size() > max_event_size - 12)
    throw ProtocolError("UC UDP datagram exceeds 16384 bytes");
  return wrap(d.event, d.reply_port);
}
Datagram decode_udp(const Bytes &b) {
  header(b);
  if (b.size() > max_event_size)
    throw ProtocolError("UC UDP datagram exceeds 16384 bytes");
  return {le16(b.data() + 4), decode_event(Bytes(b.begin() + 6, b.end()))};
}
std::vector<Event> StreamDecoder::feed(const std::uint8_t *data,
                                       std::size_t size) {
  if (failed_)
    throw ProtocolError("decoder requires reset after malformed input");
  if (!data && size)
    throw std::invalid_argument("null input");
  std::vector<Event> events;
  try {
    std::size_t offset = 0;
    while (offset < size) {
      std::size_t required = 6;
      if (pending_.size() >= 6) {
        header(pending_);
        auto length = le16(pending_.data() + 4);
        if (length < 6 || length > max_event_size)
          throw ProtocolError("invalid UC TCP length");
        required = 6 + length;
      }
      const auto take = std::min(size - offset, required - pending_.size());
      pending_.insert(pending_.end(), data + offset, data + offset + take);
      offset += take;
      if (pending_.size() < 6)
        continue;
      header(pending_);
      const auto length = le16(pending_.data() + 4);
      if (length < 6 || length > max_event_size)
        throw ProtocolError("invalid UC TCP length");
      if (pending_.size() == std::size_t(6 + length)) {
        events.push_back(
            decode_event(Bytes(pending_.begin() + 6, pending_.end())));
        pending_.clear();
      }
    }
  } catch (...) {
    failed_ = true;
    throw;
  }
  return events;
}
Bytes encode_param_value(const ParamValue &value) {
  static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559,
                "requires IEEE754 binary32");
  if (value.path.find('\0') != std::string::npos || value.path.size() > 127)
    throw ProtocolError(
        "UC parameter path must be at most 127 bytes without embedded NUL");
  Bytes out(value.path.begin(), value.path.end());
  out.push_back(0);
  put16(out, value.index);
  std::uint32_t bits;
  std::memcpy(&bits, &value.value, 4);
  for (unsigned i = 0; i < 4; ++i)
    out.push_back(std::uint8_t(bits >> (8 * i)));
  return out;
}
ParamValue decode_param_value(const Bytes &bytes) {
  auto end = std::find(bytes.begin(), bytes.end(), 0);
  auto n = std::size_t(end - bytes.begin());
  if (end == bytes.end() || n > 127 || bytes.size() != n + 7)
    throw ProtocolError("invalid parameter-value payload");
  auto p = bytes.data() + n + 1;
  auto index = le16(p);
  p += 2;
  std::uint32_t bits = std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
                       (std::uint32_t(p[2]) << 16) |
                       (std::uint32_t(p[3]) << 24);
  float value;
  std::memcpy(&value, &bits, 4);
  return {std::string(bytes.begin(), end), index, value};
}
Event make_param_value(const ParamValue &v, std::uint16_t a, std::uint16_t b) {
  return {std::uint16_t(EventType::param_value), a, b, encode_param_value(v)};
}
Event make_keep_alive(std::uint16_t a, std::uint16_t b) {
  return {std::uint16_t(EventType::keep_alive), a, b, {}};
}
} // namespace presonus::uc
