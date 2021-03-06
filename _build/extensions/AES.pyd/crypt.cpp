
#include "stdafx.h"
#include <wincrypt.h>
#include <stdio.h>
#include <stdint.h>
#include "Python.h"
#include <locale.h>
#pragma comment(lib, "crypt32.lib")


BOOL APIENTRY DllMain(HMODULE hModule,
	DWORD  ul_reason_for_call,
	LPVOID lpReserved
)
{
	switch (ul_reason_for_call)
	{
	case DLL_PROCESS_ATTACH:
	case DLL_THREAD_ATTACH:
	case DLL_THREAD_DETACH:
	case DLL_PROCESS_DETACH:
		break;
	}
	return TRUE;
}

//params: <input file> <output file> <is decrypt mode> <key>
void ErrorExit(LPTSTR lpszFunction)
{
	LPVOID lpMsgBuf;

	DWORD dw = GetLastError();

	FormatMessage(
		FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM,
		NULL,
		dw,
		GetUserDefaultUILanguage(),
		(LPTSTR)&lpMsgBuf,
		128,
		NULL
	);

	char format[] = "%s failed with error %d: %s\n";
	char buffer[200];

	_sprintf_s_l(buffer, 200, format, _get_current_locale(), lpszFunction, dw, lpMsgBuf);
	MessageBoxEx(NULL, (LPCSTR)buffer, TEXT("Error"), MB_OK, GetUserDefaultUILanguage());

	LocalFree(lpMsgBuf);
	ExitProcess(dw);
}

HCRYPTPROV GetProvider() {
	HCRYPTPROV hProv = 0;

	if (CryptAcquireContext(&hProv, NULL, MS_ENH_RSA_AES_PROV, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
		return hProv;
	}

	ErrorExit((LPTSTR) "CryptAcquireContextW");
	return 0;
	
}

HCRYPTHASH GetHash(HCRYPTPROV hProv) {
	HCRYPTHASH hHash = 0;
	if (CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash)) {
		return hHash;
	}

	CryptReleaseContext(hProv, 0);
	ErrorExit((LPTSTR) "CryptCreateHash");
	return 0;
	
}


HCRYPTKEY GetKey(HCRYPTPROV hProv, HCRYPTHASH hHash) {
	wchar_t key_str[] = L"3igcZhRdWq96m3GUmTAiv9";
	size_t len = lstrlenW(key_str);
	HCRYPTKEY hKey = 0;

	if (CryptHashData(hHash, (BYTE*)key_str, len, 0)) {
		if (CryptDeriveKey(hProv, CALG_AES_128, hHash, 0, &hKey)) {
			return hKey;
		}

		CryptDestroyHash(hHash);
		CryptReleaseContext(hProv, 0);
		ErrorExit((LPTSTR) "CryptDeriveKey");
		return 0;
	}

	CryptDestroyHash(hHash);
	CryptReleaseContext(hProv, 0);
	ErrorExit((LPTSTR) "CryptHashData");
	return 0;

}


PyObject * Encrypt(PyObject *self, PyObject *args) {
	BYTE out_buffer[4096];
	DWORD len = 0;

	Py_BEGIN_ALLOW_THREADS

	uint8_t *buffer;

	if (!PyArg_ParseTuple(args, "s#", &buffer, &len)) {
		ErrorExit((LPTSTR) "Encrypt PyArg_ParseTuple");
	}

	for (DWORD i = 0; i < len; i++) {
		out_buffer[i] = buffer[i];
	}

	out_buffer[len] = 0x0;

	HCRYPTPROV hProv = 0;
	HCRYPTHASH hHash = 0;
	HCRYPTKEY hKey = 0;

	hProv = GetProvider();
	if (!(hProv == 0)) {
		hHash = GetHash(hProv);
		if (!(hHash == 0)) {

			hKey = GetKey(hProv, hHash);
			if (!(hKey == 0)) {

				if (!CryptEncrypt(hKey, NULL, TRUE, 0, out_buffer, &len, 4096)) {
					CryptDestroyKey(hKey);
					CryptDestroyHash(hHash);
					CryptReleaseContext(hProv, 0);
					ErrorExit((LPTSTR) "CryptEncrypt");
				}
				CryptDestroyKey(hKey);
				CryptDestroyHash(hHash);
				CryptReleaseContext(hProv, 0);
			}
		}
	}
	Py_END_ALLOW_THREADS
	return PyString_FromStringAndSize((const char *)&out_buffer, (Py_ssize_t)len);
}
		


PyObject * Decrypt(PyObject *self, PyObject *args) {
	BYTE out_buffer[4096];
	DWORD len = 0;

	Py_BEGIN_ALLOW_THREADS

	uint8_t *buffer;

	if (!PyArg_ParseTuple(args, "s#", &buffer, &len)) {
		ErrorExit((LPTSTR) "Decrypt PyArg_ParseTuple");
		return NULL;
	}

	for (DWORD i = 0; i < len; i++) {
		out_buffer[i] = buffer[i];
	}
	out_buffer[len] = 0x0;

	HCRYPTPROV hProv;
	HCRYPTHASH hHash;
	HCRYPTKEY hKey;

	hProv = GetProvider();
	if (!(hProv == 0)) {
		hHash = GetHash(hProv);
		if (!(hHash == 0)) {

			hKey = GetKey(hProv, hHash);
			if (!(hKey == 0)) {

				if (!CryptDecrypt(hKey, NULL, TRUE, 0, out_buffer, &len)) {
					CryptDestroyKey(hKey);
					CryptDestroyHash(hHash);
					CryptReleaseContext(hProv, 0);
					ErrorExit((LPTSTR) "CryptDecrypt");
				}

				CryptDestroyKey(hKey);
				CryptDestroyHash(hHash);
				CryptReleaseContext(hProv, 0);
			}
		}
	}
	Py_END_ALLOW_THREADS
	return PyString_FromStringAndSize((const char *)&out_buffer, (Py_ssize_t)len);
}


static PyMethodDef methods[] = {
	{"Encrypt", Encrypt, 1, ""},
	{"Decrypt", Decrypt, 1, ""},
	
	{NULL, NULL}
};


PyMODINIT_FUNC initAES(void) {
	Py_InitModule("AES", methods);
}
