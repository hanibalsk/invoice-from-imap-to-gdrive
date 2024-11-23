import os
import PyPDF2
from PyPDF2.errors import PdfReadError

class PDFProcessor:
    def __init__(self, pdf_passwords):
        self.pdf_passwords = pdf_passwords

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        original_file = pdf_path
        tmp_file = pdf_path + ".tmp"
        decrypted_file = pdf_path + ".decrypted"

        try:
            # Rename original file to temporary name
            os.rename(original_file, tmp_file)

            # Attempt to decrypt the PDF
            with open(tmp_file, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)

                if reader.is_encrypted:
                    # Try each password to decrypt
                    for password in self.pdf_passwords:
                        try:
                            reader.decrypt(password)

                            # Test if decryption succeeded by accessing the first page
                            _ = reader.pages[0]  # Try to access the first page
                            print(f"Decryption successful with password: {password}")
                            break
                        except NotImplementedError:
                            print(f"PyCryptodome is required for AES algorithm. Unable to decrypt PDF {pdf_path}.")
                            os.rename(tmp_file, original_file)  # Restore original file
                            return text
                        except PdfReadError:
                            continue
                    else:
                        print(f"Unable to decrypt PDF {pdf_path} with provided passwords.")
                        os.rename(tmp_file, original_file)  # Restore original file
                        return text

                # Save decrypted PDF for processing
                writer = PyPDF2.PdfWriter()
                for page in reader.pages:
                    print(f"Adding page {page} to decrypted PDF")
                    writer.add_page(page)

                with open(decrypted_file, "wb") as output_file:
                    print(f"Writing decrypted PDF to {decrypted_file}")
                    writer.write(output_file)

            # Rename decrypted file back to original name
            os.rename(decrypted_file, original_file)
            print(f"Decrypted PDF saved to {original_file}")

            # Extract text from the decrypted PDF
            with open(original_file, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(reader.pages)):
                    text += reader.pages[page_num].extract_text() + "\n"

        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            # Restore the original file if something went wrong
            if os.path.exists(tmp_file):
                os.rename(tmp_file, original_file)
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            # Clean up decrypted file if left over
            if os.path.exists(decrypted_file):
                os.remove(decrypted_file)

        return text