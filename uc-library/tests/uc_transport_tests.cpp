#include "presonus/uc/transport_events.hpp"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace Presonus::UC;
using Image = std::array<unsigned char, 512>;
static std::uint32_t get32(const unsigned char *p) {
  return std::uint32_t(p[0]) | (std::uint32_t(p[1]) << 8) |
         (std::uint32_t(p[2]) << 16) | (std::uint32_t(p[3]) << 24);
}
static void put32(unsigned char *p, std::uint32_t v) {
  for (int i = 0; i < 4; ++i)
    p[i] = static_cast<unsigned char>(v >> (i * 8));
}
static void read(std::istream &in, void *p, std::size_t n) {
  if (!in.read(static_cast<char *>(p), static_cast<std::streamsize>(n)))
    throw std::runtime_error("truncated fixture");
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream in(argv[1], std::ios::binary);
  char magic[8];
  read(in, magic, 8);
  if (std::memcmp(magic, "UCTRv001", 8))
    return 3;
  unsigned char countbytes[4];
  read(in, countbytes, 4);
  auto count = get32(countbytes);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char meta[16];
    read(in, meta, 16);
    auto op = meta[1];
    auto capacity = get32(meta + 4);
    auto offset = get32(meta + 8);
    auto next = get32(meta + 12);
    Image io, event, out_io, out_event;
    read(in, io.data(), 512);
    read(in, event.data(), 512);
    read(in, out_io.data(), 512);
    read(in, out_event.data(), 512);
    BufferReader reader(io.data(), static_cast<int>(capacity),
                        static_cast<int>(offset));
    BufferWriter writer(io.data(), static_cast<int>(capacity),
                        static_cast<int>(offset));
    bool result = false;
    if (op < 2) {
      UDPMappingEvent value;
      value.mapping =
          static_cast<unsigned short>(event[16] | (unsigned(event[17]) << 8));
      UDPMappingEventClass codec;
      result = op == 0 ? codec.write(writer, value) : codec.read(value, reader);
      event[16] = static_cast<unsigned char>(value.mapping);
      event[17] = static_cast<unsigned char>(value.mapping >> 8);
    } else if (op < 4) {
      MidiMessageEvent value;
      std::memcpy(value.bytes.data(), event.data() + 16, 4);
      MidiMessageEventClass codec;
      result = op == 2 ? codec.write(writer, value) : codec.read(value, reader);
      std::memcpy(event.data() + 16, value.bytes.data(), 4);
    } else {
      ExtensionQueryEvent value;
      value.query = get32(event.data() + 16);
      ExtensionQueryEventClass codec;
      result = op == 4 ? codec.write(writer, value) : codec.read(value, reader);
      put32(event.data() + 16, value.query);
    }
    auto cursor = op % 2 ? reader.position() : writer.position();
    if (result != bool(meta[2]) || cursor != static_cast<int>(next) ||
        io != out_io || event != out_event) {
      std::cerr << "mismatch row=" << row << " role=" << unsigned(meta[0])
                << " op=" << unsigned(op) << '\n';
      return 1;
    }
  }
  if (in.peek() != std::char_traits<char>::eof())
    return 4;
  std::cout << count << " original ARM transport fixtures passed\n";
}
