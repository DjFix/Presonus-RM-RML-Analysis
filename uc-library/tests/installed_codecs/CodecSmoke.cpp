#include <array>
#include <cstdio>
#include <cstring>
#include <vector>

#include <png.h>
#include <zlib.h>

static_assert(PNG_LIBPNG_VER == 10610);
static_assert(ZLIB_VERNUM == 0x12b0);

int main(int argc, char *argv[]) {
  if (argc != 2 || png_access_version_number() != PNG_LIBPNG_VER ||
      std::strcmp(png_get_libpng_ver(nullptr), PNG_LIBPNG_VER_STRING) != 0 ||
      std::strcmp(zlibVersion(), ZLIB_VERSION) != 0)
    return 1;

  png_image image{};
  image.version = PNG_IMAGE_VERSION;
  if (!png_image_begin_read_from_file(&image, argv[1]))
    return 2;

  image.format = PNG_FORMAT_RGB;
  std::vector<unsigned char> pixels(PNG_IMAGE_SIZE(image));
  const bool decoded =
      png_image_finish_read(&image, nullptr, pixels.data(), 0, nullptr);
  png_image_free(&image);
  if (!decoded || pixels.empty())
    return 3;

  const std::array<unsigned char, 9> plain{0x00, 0x00, 0x01, 0x02, 0xff,
                                           0x03, 0x04, 0x05, 0x00};
  std::vector<unsigned char> packed(compressBound(plain.size()));
  uLongf packedSize = packed.size();
  if (compress(packed.data(), &packedSize, plain.data(), plain.size()) != Z_OK)
    return 4;

  std::array<unsigned char, plain.size()> unpacked{};
  uLongf unpackedSize = unpacked.size();
  if (uncompress(unpacked.data(), &unpackedSize, packed.data(), packedSize) !=
          Z_OK ||
      unpackedSize != plain.size() || unpacked != plain)
    return 5;

  std::printf("libpng %s, zlib %s\n", png_get_libpng_ver(nullptr),
              zlibVersion());
}
