#pragma once

// Portable result type. The native result points into immutable string storage;
// its original C++ return declaration remains unresolved.
const char *getDFUErr(int code);
