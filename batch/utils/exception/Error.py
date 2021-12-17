# -*- coding: utf-8 -*-


class LicenseUpdateError(Exception):
  def __init__(self, message:str, page=None):
    super(LicenseUpdateError, self).__init__(message)
    self.__error_page = page

  @property
  def error_page(self):
    return self.__error_page


  @error_page.setter
  def error_page(self, page):
    self.__error_page = page
