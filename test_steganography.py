import os
import tempfile
import unittest
from PIL import Image
import numpy as np
from datetime import datetime
from img import SteganographyLogic
from gif import GIFSteganographyLogic
import logging
import struct
import shutil

# Setup logging for tests
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

class TestSteganography(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.img_logic = SteganographyLogic()
        self.gif_logic = GIFSteganographyLogic()
        
        # Create test files
        self.carrier_img = os.path.join(self.test_dir, "carrier.png")
        self.carrier_gif = os.path.join(self.test_dir, "carrier.gif")
        self.test_file = os.path.join(self.test_dir, "test.txt")
        self.output_img = os.path.join(self.test_dir, "output.png")
        self.output_gif = os.path.join(self.test_dir, "output.gif")
        
        # Create a larger carrier image (1024x1024)
        img = Image.new('RGB', (1024, 1024), color='white')
        img.save(self.carrier_img)
        
        # Create a small carrier GIF (100x100, 2 frames)
        frames = [
            Image.new('RGB', (100, 100), color='red'),
            Image.new('RGB', (100, 100), color='blue')
        ]
        frames[0].save(
            self.carrier_gif,
            save_all=True,
            append_images=[frames[1]],
            duration=500,
            loop=0
        )
        
        # Create a small test file (1KB)
        with open(self.test_file, 'w') as f:
            f.write('A' * 1024)
        
        # Test parameters
        self.key = self.img_logic.generate_key()
        self.password = "testpassword123"
        self.author = "Test Author"
        
        # Progress callback for testing
        self.progress_values = []
        
    def progress_callback(self, value):
        """Record progress values."""
        self.progress_values.append(value)
        logging.info(f"Progress: {value}%")
        
    def test_image_key_generation(self):
        """Test key generation for image steganography."""
        key = self.img_logic.generate_key()
        self.assertIsNotNone(key)
        self.assertTrue(len(key) > 0)
        
    def test_gif_key_generation(self):
        """Test key generation for GIF steganography."""
        key = self.gif_logic.generate_key()
        self.assertIsNotNone(key)
        self.assertTrue(len(key) > 0)
        
    def test_image_cipher_initialization(self):
        """Test cipher initialization for image steganography."""
        cipher = self.img_logic.get_cipher(self.key)
        self.assertIsNotNone(cipher)
        
    def test_gif_cipher_initialization(self):
        """Test cipher initialization for GIF steganography."""
        cipher = self.gif_logic.get_cipher(self.key)
        self.assertIsNotNone(cipher)
        
    def test_image_embed_extract_no_password(self):
        try:
            # Create output directory
            output_dir = os.path.join(self.test_dir, "image_output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Embed data
            self.img_logic.embed_data_optimized(
                self.carrier_img,
                [self.test_file],
                self.key,
                None,
                self.author,
                self.progress_callback
            )
            
            # Extract data
            extracted_files = self.img_logic.extract_data_optimized(
                self.carrier_img,
                output_dir,
                self.key,
                None,
                self.progress_callback
            )
            
            self.assertTrue(len(extracted_files) > 0)
            self.assertTrue(os.path.exists(extracted_files[0]))
            
            # Verify content
            with open(self.test_file, 'rb') as f1, open(extracted_files[0], 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())
                
        except Exception as e:
            logging.error(f"Error in image test: {str(e)}")
            raise

    def test_image_embed_extract_with_password(self):
        try:
            # Create output directory
            output_dir = os.path.join(self.test_dir, "image_password_output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Embed data
            self.img_logic.embed_data_optimized(
                self.carrier_img,
                [self.test_file],
                self.key,
                self.password,
                self.author,
                self.progress_callback
            )
            
            # Extract data
            extracted_files = self.img_logic.extract_data_optimized(
                self.carrier_img,
                output_dir,
                self.key,
                self.password,
                self.progress_callback
            )
            
            self.assertTrue(len(extracted_files) > 0)
            self.assertTrue(os.path.exists(extracted_files[0]))
            
            # Verify content
            with open(self.test_file, 'rb') as f1, open(extracted_files[0], 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())
                
        except Exception as e:
            logging.error(f"Error in image password test: {str(e)}")
            raise

    def test_gif_embed_extract_no_password(self):
        try:
            # Create output directory
            output_dir = os.path.join(self.test_dir, "gif_output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a test GIF with proper format
            frames = [
                Image.new('RGB', (100, 100), color='red'),
                Image.new('RGB', (100, 100), color='blue')
            ]
            frames[0].save(
                self.carrier_gif,
                save_all=True,
                append_images=[frames[1]],
                duration=500,
                loop=0
            )
            
            # Embed data
            output_data = self.gif_logic.embed_data(
                self.carrier_gif,
                [self.test_file],
                self.key,
                None,  # no password
                None,  # no author
                self.progress_callback
            )
            
            # Save the output GIF
            with open(self.output_gif, 'wb') as f:
                f.write(output_data)
            
            # Extract data
            extracted_files = self.gif_logic.extract_data(
                self.output_gif,
                output_dir,
                self.key,
                None,  # no password
                self.progress_callback
            )
            
            self.assertTrue(len(extracted_files) > 0)
            self.assertTrue(os.path.exists(extracted_files[0]))
            
            # Verify content
            with open(self.test_file, 'rb') as f1, open(extracted_files[0], 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())
                
        except Exception as e:
            logging.error(f"Error in GIF test: {str(e)}")
            raise

    def test_gif_embed_extract_with_password(self):
        try:
            # Create output directory
            output_dir = os.path.join(self.test_dir, "gif_password_output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a test GIF with proper format
            frames = [
                Image.new('RGB', (100, 100), color='red'),
                Image.new('RGB', (100, 100), color='blue')
            ]
            frames[0].save(
                self.carrier_gif,
                save_all=True,
                append_images=[frames[1]],
                duration=500,
                loop=0
            )
            
            # Embed data
            output_data = self.gif_logic.embed_data(
                self.carrier_gif,
                [self.test_file],
                self.key,
                self.password,
                self.author,
                self.progress_callback
            )
            
            # Save the output GIF
            with open(self.output_gif, 'wb') as f:
                f.write(output_data)
            
            # Extract data
            extracted_files = self.gif_logic.extract_data(
                self.output_gif,
                output_dir,
                self.key,
                self.password,
                self.progress_callback
            )
            
            self.assertTrue(len(extracted_files) > 0)
            self.assertTrue(os.path.exists(extracted_files[0]))
            
            # Verify content
            with open(self.test_file, 'rb') as f1, open(extracted_files[0], 'rb') as f2:
                self.assertEqual(f1.read(), f2.read())
                
        except Exception as e:
            logging.error(f"Error in GIF password test: {str(e)}")
            raise

    def test_password_validation(self):
        """Test password validation for both image and GIF."""
        try:
            # Test with image
            output_path = os.path.join(self.test_dir, 'output_stego_pwd.png')
            self.img_logic.embed_data_optimized(
                self.carrier_img,
                [self.test_file],
                self.key,
                self.password,
                self.author,
                self.progress_callback
            )
            
            # Test with wrong password
            with self.assertRaises(ValueError):
                self.img_logic.extract_data_optimized(
                    self.carrier_img,
                    self.test_dir,
                    self.key,
                    "wrongpassword",
                    self.progress_callback
                )
                
            # Test with GIF
            small_gif = Image.new('RGB', (50, 50), color='white')
            small_gif_path = os.path.join(self.test_dir, 'small_carrier_pwd.gif')
            small_gif.save(small_gif_path, 'GIF')
            
            output_path = os.path.join(self.test_dir, 'output_stego_pwd.gif')
            result = self.gif_logic.embed_data(
                small_gif_path,
                [self.test_file],
                self.key,
                self.password,
                self.author,
                self.progress_callback
            )
            
            with open(output_path, 'wb') as f:
                f.write(result)
                
            # Test with wrong password
            with self.assertRaises(ValueError):
                self.gif_logic.extract_data(
                    output_path,
                    self.test_dir,
                    self.key,
                    "wrongpassword",
                    self.progress_callback
                )
        except Exception as e:
            logging.error(f"Password validation test failed: {str(e)}")
            raise
            
    def test_metadata_handling(self):
        """Test metadata handling for both image and GIF."""
        try:
            # Create a small test GIF
            small_gif = Image.new('RGB', (50, 50), color='white')
            small_gif_path = os.path.join(self.test_dir, 'small_carrier_meta.gif')
            small_gif.save(small_gif_path, 'GIF')
            
            # Test with GIF
            output_path = os.path.join(self.test_dir, 'output_stego_meta.gif')
            result = self.gif_logic.embed_data(
                small_gif_path,
                [self.test_file],
                self.key,
                self.password,
                self.author,
                self.progress_callback
            )
            
            with open(output_path, 'wb') as f:
                f.write(result)
                
            # View metadata
            author, timestamp = self.gif_logic.view_metadata(
                output_path,
                self.key,
                self.password,
                self.progress_callback
            )
            
            self.assertEqual(author.strip(), self.author.strip())
            self.assertIsNotNone(timestamp)
        except Exception as e:
            logging.error(f"Metadata handling test failed: {str(e)}")
            raise
        
    def tearDown(self):
        """Clean up test files."""
        try:
            shutil.rmtree(self.test_dir)
        except Exception as e:
            logging.error(f"Cleanup failed: {str(e)}")

if __name__ == '__main__':
    unittest.main(verbosity=2) 