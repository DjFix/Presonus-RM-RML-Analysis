#include "presonus/uc/events.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
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
    p[i] = static_cast<unsigned char>(v >> (8 * i));
}
static Event header(const Image &image) {
  return {get32(image.data()), get32(image.data() + 4), get32(image.data() + 8),
          get32(image.data() + 12)};
}
static void save(Image &image, const Event &e) {
  put32(image.data(), e.type);
  put32(image.data() + 4, e.reserved04);
  put32(image.data() + 8, e.routeA);
  put32(image.data() + 12, e.routeB);
}
static unsigned short get16(const unsigned char *p) {
  return static_cast<unsigned short>(p[0] | (unsigned(p[1]) << 8));
}
static void put16(unsigned char *p, unsigned short v) {
  p[0] = static_cast<unsigned char>(v);
  p[1] = static_cast<unsigned char>(v >> 8);
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
  if (std::memcmp(magic, "UCEVv001", 8))
    return 3;
  unsigned char countbytes[4];
  read(in, countbytes, 4);
  auto count = get32(countbytes);
  for (std::uint32_t row = 0; row < count; ++row) {
    unsigned char metadata[16];
    read(in, metadata, 16);
    auto op = metadata[1];
    auto capacity = get32(metadata + 4);
    auto offset = get32(metadata + 8);
    auto next = get32(metadata + 12);
    Image io, event, expected_io, expected_event;
    read(in, io.data(), 512);
    read(in, event.data(), 512);
    read(in, expected_io.data(), 512);
    read(in, expected_event.data(), 512);
    BufferReader reader(io.data(), static_cast<int>(capacity),
                        static_cast<int>(offset));
    BufferWriter writer(io.data(), static_cast<int>(capacity),
                        static_cast<int>(offset));
    bool result = false;
    if (op < 2) {
      auto value = header(event);
      EventClass codec;
      result = op == 0 ? codec.write(writer, value) : codec.read(value, reader);
      save(event, value);
    } else if (op < 4) {
      ParamValueEvent value;
      value.header = header(event);
      std::memcpy(value.path.data(), event.data() + 16, 128);
      value.index = get16(event.data() + 144);
      std::memcpy(value.reserved92.data(), event.data() + 146, 2);
      value.valueBits = get32(event.data() + 148);
      ParamValueEventClass codec;
      result = op == 2 ? codec.write(writer, value) : codec.read(value, reader);
      save(event, value.header);
      std::memcpy(event.data() + 16, value.path.data(), 128);
      put16(event.data() + 144, value.index);
      std::memcpy(event.data() + 146, value.reserved92.data(), 2);
      put32(event.data() + 148, value.valueBits);
    } else {
      ParamStringEvent value;
      value.header = header(event);
      std::memcpy(value.path.data(), event.data() + 16, 128);
      value.index = get16(event.data() + 144);
      std::memcpy(value.text.data(), event.data() + 146, 256);
      ParamStringEventClass codec;
      result = op == 4 ? codec.write(writer, value) : codec.read(value, reader);
      save(event, value.header);
      std::memcpy(event.data() + 16, value.path.data(), 128);
      put16(event.data() + 144, value.index);
      std::memcpy(event.data() + 146, value.text.data(), 256);
    }
    auto cursor = op % 2 ? reader.position() : writer.position();
    if (result != bool(metadata[2]) || cursor != static_cast<int>(next) ||
        io != expected_io || event != expected_event) {
      std::cerr << "mismatch row=" << row << " role=" << unsigned(metadata[0])
                << " op=" << unsigned(op) << " capacity=" << capacity
                << " offset=" << offset << " result=" << result << "/"
                << unsigned(metadata[2]) << " cursor=" << cursor << "/" << next
                << " io=" << (io == expected_io)
                << " event=" << (event == expected_event) << '\n';
      return 1;
    }
  }
  if (in.peek() != std::char_traits<char>::eof())
    return 6;
  std::cout << count << " original ARM event fixtures passed\n";
}
