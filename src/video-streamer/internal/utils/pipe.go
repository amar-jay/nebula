package utils

import "os"

func RemovePipe(pipeName string) error {
	// remove the named pipe if it exists
	err := os.Remove(pipeName)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}
