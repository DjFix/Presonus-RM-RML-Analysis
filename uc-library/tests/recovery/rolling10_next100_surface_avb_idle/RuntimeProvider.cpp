#include <cstdint>
// Independent oracle adapter: invoke actual dynamic GCC signed128 runtime.
// Product uses signed64 division; this code never calls reconstructed onIdle.
extern "C" __int128 __divti3(__int128, __int128);
extern "C" __int128 __modti3(__int128, __int128);
extern "C" void divideRawClock(std::int64_t value, std::int64_t *quotient,
                               std::int64_t *remainder) {
  const __int128 wide = value;
  const __int128 divisor = 1000000;
  *quotient = static_cast<std::int64_t>(__divti3(wide, divisor));
  *remainder = static_cast<std::int64_t>(__modti3(wide, divisor));
}
