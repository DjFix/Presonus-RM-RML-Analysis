#pragma once
// Test adapter only. Addresses originate exclusively in the SHA-bound postlink
// symbol map; no production symbol/export or original ARM ABI is invented.
#include "core/public/coretypes.h"
#include <cerrno>
#if !defined(__x86_64__) || __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error This test adapter requires the canonical ELF64LSB x86_64 host
#endif
static_assert(sizeof(void *) == 8 && sizeof(Core::int64) == 8);
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <elf.h>
#include <limits>
#include <link.h>
#include <stdexcept>
#include <string>

namespace current104_test {
inline std::uintptr_t environmentWord(const char *name) {
  const char *text = std::getenv(name);
  if (!text || !*text)
    throw std::runtime_error(std::string("Missing exact symbol map field: ") +
                             name);
  errno = 0;
  char *end = nullptr;
  const auto value = std::strtoull(text, &end, 16);
  if (errno || !end || *end ||
      value > std::numeric_limits<std::uintptr_t>::max())
    throw std::runtime_error("Invalid exact mapped address/size");
  return static_cast<std::uintptr_t>(value);
}
inline unsigned elfType(const char *name) {
  const char *text = std::getenv(name);
  if (text && std::strcmp(text, "ET_DYN") == 0)
    return ET_DYN;
  if (text && std::strcmp(text, "ET_EXEC") == 0)
    return ET_EXEC;
  throw std::runtime_error("Exact mapped ELF type missing");
}
struct Request {
  std::uintptr_t value, size, bias = 0, address = 0;
  unsigned requiredFlags, type;
  bool mainImage;
  std::uintptr_t expectedBias;
  std::string expectedDso;
  unsigned images = 0, segments = 0;
};
inline int locate(dl_phdr_info *image, std::size_t, void *opaque) {
  auto &r = *static_cast<Request *>(opaque);
  const bool main = !image->dlpi_name || !image->dlpi_name[0];
  if (r.mainImage ? !main
                  : (main || image->dlpi_addr != r.expectedBias ||
                     r.expectedDso != image->dlpi_name))
    return 0;
  ++r.images;
  r.bias = image->dlpi_addr;
  if ((r.type == ET_EXEC && r.bias != 0) || !r.size ||
      r.value > std::numeric_limits<std::uintptr_t>::max() - r.bias)
    return 0;
  const auto address = r.bias + r.value;
  for (unsigned i = 0; i < image->dlpi_phnum; ++i) {
    const auto &segment = image->dlpi_phdr[i];
    if (segment.p_type != PT_LOAD ||
        (segment.p_flags & r.requiredFlags) != r.requiredFlags ||
        segment.p_vaddr > std::numeric_limits<std::uintptr_t>::max() - r.bias)
      continue;
    const auto first = r.bias + segment.p_vaddr;
    // Subtractions avoid integer wrapping in every range/size comparison.
    if (address >= first && address - first <= segment.p_memsz &&
        r.size <= segment.p_memsz - (address - first) &&
        (!(r.requiredFlags & PF_X) ||
         (address - first <= segment.p_filesz &&
          r.size <= segment.p_filesz - (address - first)))) {
      ++r.segments;
      r.address = address;
    }
  }
  return 0;
}
inline std::uintptr_t mainLocal(const char *addressName, const char *sizeName,
                                unsigned flags) {
  Request r{environmentWord(addressName),
            environmentWord(sizeName),
            0,
            0,
            flags,
            elfType("PRESONUS_LPC_ELF_TYPE"),
            true,
            0,
            ""};
  dl_iterate_phdr(locate, &r);
  if (r.images != 1 || r.segments != 1 || !r.address)
    throw std::runtime_error("Exact main local symbol/load segment mismatch");
  return r.address;
}
inline std::uintptr_t dsoLocal(void *handle, const char *addressName,
                               const char *sizeName, unsigned flags) {
  if (elfType("PRESONUS_UPDATER_ELF_TYPE") != ET_DYN)
    throw std::runtime_error("Updater body must be actual ET_DYN DSO");
  link_map *map = nullptr;
  if (!handle || dlinfo(handle, RTLD_DI_LINKMAP, &map) || !map ||
      !map->l_name || !*map->l_name)
    throw std::runtime_error("Actual DSO handle/link map unavailable");
  Request r{environmentWord(addressName),
            environmentWord(sizeName),
            0,
            0,
            flags,
            ET_DYN,
            false,
            static_cast<std::uintptr_t>(map->l_addr),
            map->l_name};
  dl_iterate_phdr(locate, &r);
  if (r.images != 1 || r.segments != 1 || !r.address)
    throw std::runtime_error("Exact DSO local symbol/load segment mismatch");
  return r.address;
}
inline void seedLpcStartMilliseconds() {
  const auto size = environmentWord("PRESONUS_LPC_START_SIZE");
  if (size != 8)
    throw std::runtime_error("LPC timestamp symbol must have exact size8");
  auto address =
      mainLocal("PRESONUS_LPC_START_ADDR", "PRESONUS_LPC_START_SIZE", PF_W);
  if (address % alignof(Core::int64))
    throw std::runtime_error("LPC timestamp alignment mismatch");
  *reinterpret_cast<Core::int64 *>(address) = 1000;
}
inline unsigned lpcRawEncode(unsigned char *out, unsigned count,
                             unsigned char *input) {
  using Function = unsigned (*)(unsigned char *, unsigned, unsigned char *);
  return reinterpret_cast<Function>(mainLocal("PRESONUS_LPC_RAW_ADDR",
                                              "PRESONUS_LPC_RAW_SIZE",
                                              PF_X))(out, count, input);
}
inline unsigned updaterOriginalCallback(void *handle, void *data, unsigned size,
                                        unsigned count, void *context) {
  using Function = unsigned (*)(void *, unsigned, unsigned, void *);
  return reinterpret_cast<Function>(dsoLocal(
      handle, "PRESONUS_UPDATER_CALLBACK_ADDR",
      "PRESONUS_UPDATER_CALLBACK_SIZE", PF_X))(data, size, count, context);
}
} // namespace current104_test
